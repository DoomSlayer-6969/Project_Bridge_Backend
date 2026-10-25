import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import ConversationRepoDep, CurrentUserDep, MessageRepoDep, UserRepoDep
from app.models import DEFAULT_PREFERENCES, Conversation, Message, User
from app.repositories import ConversationRepository
from app.schemas import (
    ConversationCreateRequest,
    ConversationResponse,
    MessageCreateRequest,
    MessageResponse,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])

OffsetQuery = Annotated[int, Query(ge=0)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]


async def _get_own_conversation(
    conversation_id: uuid.UUID, user: User, conversations: ConversationRepository
) -> Conversation:
    """The user's conversation; 404 if it doesn't exist or belongs to someone else."""
    conversation = await conversations.get(conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conversation


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def start_conversation(
    payload: ConversationCreateRequest, user: CurrentUserDep, conversations: ConversationRepoDep
) -> Conversation:
    return await conversations.add(
        Conversation(user_id=user.id, initial_mode=payload.initial_mode)
    )


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    user: CurrentUserDep,
    conversations: ConversationRepoDep,
    offset: OffsetQuery = 0,
    limit: LimitQuery = 50,
) -> list[Conversation]:
    """The user's conversations, newest first."""
    return await conversations.list_for_user(user.id, offset=offset, limit=limit)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: uuid.UUID, user: CurrentUserDep, conversations: ConversationRepoDep
) -> Conversation:
    return await _get_own_conversation(conversation_id, user, conversations)


@router.post("/{conversation_id}/end", response_model=ConversationResponse)
async def end_conversation(
    conversation_id: uuid.UUID, user: CurrentUserDep, conversations: ConversationRepoDep
) -> Conversation:
    conversation = await _get_own_conversation(conversation_id, user, conversations)
    if conversation.ended_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Conversation has already ended")
    conversation.ended_at = datetime.now(UTC)
    return await conversations.update(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID, user: CurrentUserDep, conversations: ConversationRepoDep
) -> None:
    """Delete the conversation; its messages are removed by the database cascade."""
    conversation = await _get_own_conversation(conversation_id, user, conversations)
    await conversations.delete(conversation)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreateRequest,
    user: CurrentUserDep,
    conversations: ConversationRepoDep,
    messages: MessageRepoDep,
    users: UserRepoDep,
) -> Message:
    """Store a user message. `memory_allowed` is stored as true only if the user's preferences
    also allow memory; messages stored with false must never be sent to the LLM."""
    conversation = await _get_own_conversation(conversation_id, user, conversations)
    if conversation.ended_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Conversation has ended")
    preferences = await users.get_preferences(user.id)
    memory_preference = (
        preferences.memory_allowed if preferences else DEFAULT_PREFERENCES["memory_allowed"]
    )
    return await messages.add(
        Message(
            conversation_id=conversation.id,
            sender="user",
            content=payload.content,
            active_mode=payload.active_mode,
            memory_allowed=payload.memory_allowed and memory_preference,
        )
    )


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: uuid.UUID,
    user: CurrentUserDep,
    conversations: ConversationRepoDep,
    messages: MessageRepoDep,
    offset: OffsetQuery = 0,
    limit: LimitQuery = 100,
) -> list[Message]:
    """The conversation's messages, oldest first (chat order)."""
    conversation = await _get_own_conversation(conversation_id, user, conversations)
    return await messages.list_for_conversation(conversation.id, offset=offset, limit=limit)
