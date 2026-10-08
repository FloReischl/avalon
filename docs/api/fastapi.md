# FastAPI API

> Generated from the FastAPI OpenAPI contract. Do not edit manually.

API: Avalon Backend
OpenAPI: 3.1.0

The complete machine-readable contract is available in `openapi.json`.

## Endpoints

### `GET /api/v1/assets/avatar/greeting`

Avatar Greeting Audio

Return the configured greeting audio of the effective avatar.

Operation ID: `avatar_greeting_audio_api_v1_assets_avatar_greeting_get`

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {}
      }
    },
    "description": "Successful Response"
  }
}
```

### `GET /api/v1/assets/avatar/images/{key}`

Avatar Image

Return one configured image of the effective avatar by logical key.

Operation ID: `avatar_image_api_v1_assets_avatar_images__key__get`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "key",
    "required": true,
    "schema": {
      "title": "Key",
      "type": "string"
    }
  }
]
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {}
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `GET /api/v1/attachments/{attachment_id}/download`

Download Attachment

Download one immutable Avalon attachment.

Operation ID: `download_attachment_api_v1_attachments__attachment_id__download_get`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "attachment_id",
    "required": true,
    "schema": {
      "title": "Attachment Id",
      "type": "integer"
    }
  }
]
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {}
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `POST /api/v1/audio/call/end`

End Audio Call

End the call and re-enable Whisper's idle lifecycle.

Operation ID: `end_audio_call_api_v1_audio_call_end_post`

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/AudioCallStatusResponse"
        }
      }
    },
    "description": "Successful Response"
  }
}
```

### `POST /api/v1/audio/call/speech/consume`

Consume Audio Call Speech

Return and clear one assistant response reserved for avatar TTS.

Operation ID: `consume_audio_call_speech_api_v1_audio_call_speech_consume_post`

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "additionalProperties": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "title": "Response Consume Audio Call Speech Api V1 Audio Call Speech Consume Post",
          "type": "object"
        }
      }
    },
    "description": "Successful Response"
  }
}
```

### `POST /api/v1/audio/call/start`

Start Audio Call

Warm LLM and Whisper before publishing an active audio call.

Operation ID: `start_audio_call_api_v1_audio_call_start_post`

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/AudioCallStartRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/AudioCallStatusResponse"
        }
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `GET /api/v1/audio/call/status`

Get Audio Call Status

Return the global audio-call state for any frontend window.

Operation ID: `get_audio_call_status_api_v1_audio_call_status_get`

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/AudioCallStatusResponse"
        }
      }
    },
    "description": "Successful Response"
  }
}
```

### `POST /api/v1/audio/call/turn/complete`

Complete Audio Call Turn

Mark the active avatar call turn complete after local TTS playback.

Operation ID: `complete_audio_call_turn_api_v1_audio_call_turn_complete_post`

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/AudioCallStatusResponse"
        }
      }
    },
    "description": "Successful Response"
  }
}
```

### `POST /api/v1/audio/dialog/turn`

Create Dialog Turn

Wait for one speech turn and stream Gemma's response.

Operation ID: `create_dialog_turn_api_v1_audio_dialog_turn_post`

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/AudioResponseRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {}
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `POST /api/v1/audio/recording/abort`

Abort Audio Recording

Discard an active backend-local microphone recording.

Operation ID: `abort_audio_recording_api_v1_audio_recording_abort_post`

**Responses**

```json
{
  "204": {
    "description": "Successful Response"
  }
}
```

### `POST /api/v1/audio/recording/start`

Start Audio Recording

Start one backend-local microphone recording.

Operation ID: `start_audio_recording_api_v1_audio_recording_start_post`

**Responses**

```json
{
  "204": {
    "description": "Successful Response"
  }
}
```

### `POST /api/v1/audio/recording/stop`

Stop Audio Recording

Stop capture and stream Gemma's response using prior chat context.

Operation ID: `stop_audio_recording_api_v1_audio_recording_stop_post`

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/AudioResponseRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {}
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `GET /api/v1/authorization-requests`

List Pending Authorization Requests

List all pending requests for the global permission inbox.

Operation ID: `list_pending_authorization_requests_api_v1_authorization_requests_get`

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "items": {
            "$ref": "#/components/schemas/PendingAuthorizationRequestResponse"
          },
          "title": "Response List Pending Authorization Requests Api V1 Authorization Requests Get",
          "type": "array"
        }
      }
    },
    "description": "Successful Response"
  }
}
```

### `POST /api/v1/authorization-requests/{request_id}/abort`

Abort Authorization

Abort the waiting agent operation.

Operation ID: `abort_authorization_api_v1_authorization_requests__request_id__abort_post`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "request_id",
    "required": true,
    "schema": {
      "title": "Request Id",
      "type": "string"
    }
  }
]
```

**Responses**

```json
{
  "204": {
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `POST /api/v1/authorization-requests/{request_id}/confirm`

Confirm Authorization

Resume one pending request with the selected original items.

Operation ID: `confirm_authorization_api_v1_authorization_requests__request_id__confirm_post`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "request_id",
    "required": true,
    "schema": {
      "title": "Request Id",
      "type": "string"
    }
  }
]
```

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/AuthorizationDecisionRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "204": {
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `POST /api/v1/chat`

Create Chat Response

Persist and stream one text-chat turn as Avalon SSE events.

Operation ID: `create_chat_response_api_v1_chat_post`

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/ChatRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {}
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `GET /api/v1/chats`

List Chats

Return all persistent chats ordered by recent activity.

Operation ID: `list_chats_api_v1_chats_get`

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "items": {
            "$ref": "#/components/schemas/ChatSummaryResponse"
          },
          "title": "Response List Chats Api V1 Chats Get",
          "type": "array"
        }
      }
    },
    "description": "Successful Response"
  }
}
```

### `GET /api/v1/chats/{chat_id}`

Get Chat

Return one persistent chat with its complete message history.

Operation ID: `get_chat_api_v1_chats__chat_id__get`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "chat_id",
    "required": true,
    "schema": {
      "title": "Chat Id",
      "type": "integer"
    }
  }
]
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ChatDetailResponse"
        }
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `PATCH /api/v1/chats/{chat_id}`

Rename Chat

Rename one persistent chat manually.

Operation ID: `rename_chat_api_v1_chats__chat_id__patch`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "chat_id",
    "required": true,
    "schema": {
      "title": "Chat Id",
      "type": "integer"
    }
  }
]
```

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/RenameChatRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ChatSummaryResponse"
        }
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `DELETE /api/v1/chats/{chat_id}`

Delete Chat

Physically delete one persistent chat and its messages.

Operation ID: `delete_chat_api_v1_chats__chat_id__delete`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "chat_id",
    "required": true,
    "schema": {
      "title": "Chat Id",
      "type": "integer"
    }
  }
]
```

**Responses**

```json
{
  "204": {
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `GET /api/v1/chats/{chat_id}/permissions`

List Proactive Permissions

Show active grants/configured permissions for one chat's agent.

Operation ID: `list_proactive_permissions_api_v1_chats__chat_id__permissions_get`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "chat_id",
    "required": true,
    "schema": {
      "title": "Chat Id",
      "type": "integer"
    }
  }
]
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "items": {
            "$ref": "#/components/schemas/ProactivePermissionResponse"
          },
          "title": "Response List Proactive Permissions Api V1 Chats  Chat Id  Permissions Get",
          "type": "array"
        }
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `PUT /api/v1/chats/{chat_id}/permissions/{permission_id}`

Save Proactive Permission

Directly persist a proactive duration or permanent grant for this chat.

Operation ID: `save_proactive_permission_api_v1_chats__chat_id__permissions__permission_id__put`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "chat_id",
    "required": true,
    "schema": {
      "title": "Chat Id",
      "type": "integer"
    }
  },
  {
    "in": "path",
    "name": "permission_id",
    "required": true,
    "schema": {
      "title": "Permission Id",
      "type": "integer"
    }
  }
]
```

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/ProactivePermissionUpdateRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ProactivePermissionResponse"
        }
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `PATCH /api/v1/chats/{chat_id}/pinned`

Set Chat Pinned

Persist the pinned state of one chat.

Operation ID: `set_chat_pinned_api_v1_chats__chat_id__pinned_patch`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "chat_id",
    "required": true,
    "schema": {
      "title": "Chat Id",
      "type": "integer"
    }
  }
]
```

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/SetChatPinnedRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ChatSummaryResponse"
        }
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `GET /api/v1/events`

Events

Expose all existing local invalidations through one SSE connection.

Operation ID: `events_api_v1_events_get`

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {}
      }
    },
    "description": "Successful Response"
  }
}
```

### `POST /api/v1/llm/text`

Generate Text

Run non-streaming text inference without chat state or persistence.

Operation ID: `generate_text_api_v1_llm_text_post`

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/LlmTextRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/LlmTextResponse"
        }
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `POST /api/v1/messages/{message_id}/attachments`

Upload Attachment

Create one file attachment and directly link it to a message.

Operation ID: `upload_attachment_api_v1_messages__message_id__attachments_post`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "message_id",
    "required": true,
    "schema": {
      "title": "Message Id",
      "type": "integer"
    }
  }
]
```

**Request body**

```json
{
  "content": {
    "multipart/form-data": {
      "schema": {
        "$ref": "#/components/schemas/Body_upload_attachment_api_v1_messages__message_id__attachments_post"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "201": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/AttachmentResponse"
        }
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `POST /api/v1/runtime/warm-up`

Warm Up Runtime

Make the configured local model resident without creating chat state.

Operation ID: `warm_up_runtime_api_v1_runtime_warm_up_post`

**Responses**

```json
{
  "204": {
    "description": "Successful Response"
  }
}
```

### `POST /api/v1/tts`

Synthesize Speech

Synthesize plain text and return one complete WAV response.

Operation ID: `synthesize_speech_api_v1_tts_post`

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/TtsRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {}
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `POST /api/v1/tts/playback-ended`

Playback Ended

Notify the backend that a frontend playback has stopped.

Operation ID: `playback_ended_api_v1_tts_playback_ended_post`

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/TtsPlaybackEndedRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "204": {
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `GET /api/v1/ui/config`

Ui Config

Return only configuration intentionally exposed to the frontend.

Operation ID: `ui_config_api_v1_ui_config_get`

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/UiConfigResponse"
        }
      }
    },
    "description": "Successful Response"
  }
}
```

### `PUT /api/v1/ui/settings`

Update User Settings

Update user settings (e.g. avatar zoom).

Operation ID: `update_user_settings_api_v1_ui_settings_put`

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/UserSettingsUpdateRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "additionalProperties": true,
          "title": "Response Update User Settings Api V1 Ui Settings Put",
          "type": "object"
        }
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `GET /api/v1/ui/token`

Ui Agent Token

Return a fresh local bearer token for one persisted agent.

Operation ID: `ui_agent_token_api_v1_ui_token_get`

**Parameters**

```json
[
  {
    "in": "query",
    "name": "agent_id",
    "required": true,
    "schema": {
      "exclusiveMinimum": 0,
      "title": "Agent Id",
      "type": "integer"
    }
  }
]
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/AgentTokenResponse"
        }
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `GET /api/v1/workflow-executions/confirmations/pending`

Pending Confirmation

Expose the pending confirmation to Avalon’s local Human-UI boundary.

Operation ID: `pending_confirmation_api_v1_workflow_executions_confirmations_pending_get`

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "anyOf": [
            {
              "$ref": "#/components/schemas/WorkflowConfirmationResponse"
            },
            {
              "type": "null"
            }
          ],
          "title": "Response Pending Confirmation Api V1 Workflow Executions Confirmations Pending Get"
        }
      }
    },
    "description": "Successful Response"
  }
}
```

### `POST /api/v1/workflow-executions/confirmations/{confirmation_id}/cancel`

Cancel Confirmation

Operation ID: `cancel_confirmation_api_v1_workflow_executions_confirmations__confirmation_id__cancel_post`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "confirmation_id",
    "required": true,
    "schema": {
      "title": "Confirmation Id",
      "type": "string"
    }
  }
]
```

**Responses**

```json
{
  "204": {
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `POST /api/v1/workflow-executions/confirmations/{confirmation_id}/confirm`

Confirm Confirmation

Operation ID: `confirm_confirmation_api_v1_workflow_executions_confirmations__confirmation_id__confirm_post`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "confirmation_id",
    "required": true,
    "schema": {
      "title": "Confirmation Id",
      "type": "string"
    }
  }
]
```

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/WorkflowConfirmationSubmitRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "204": {
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `POST /api/v1/workflow-executions/{execution_id}/confirmation`

Request Confirmation

Block one owned running workflow until its confirmation is resolved.

Operation ID: `request_confirmation_api_v1_workflow_executions__execution_id__confirmation_post`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "execution_id",
    "required": true,
    "schema": {
      "title": "Execution Id",
      "type": "integer"
    }
  }
]
```

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/WorkflowConfirmationRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "items": {
            "additionalProperties": true,
            "type": "object"
          },
          "title": "Response Request Confirmation Api V1 Workflow Executions  Execution Id  Confirmation Post",
          "type": "array"
        }
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `PATCH /api/v1/workflow-executions/{execution_id}/runtime`

Update Runtime

Operation ID: `update_runtime_api_v1_workflow_executions__execution_id__runtime_patch`

**Parameters**

```json
[
  {
    "in": "path",
    "name": "execution_id",
    "required": true,
    "schema": {
      "title": "Execution Id",
      "type": "integer"
    }
  }
]
```

**Request body**

```json
{
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/WorkflowRuntimeUpdateRequest"
      }
    }
  },
  "required": true
}
```

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {}
      }
    },
    "description": "Successful Response"
  },
  "422": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HTTPValidationError"
        }
      }
    },
    "description": "Validation Error"
  }
}
```

### `GET /health`

Health

Report that the HTTP backend is ready.

Operation ID: `health_health_get`

**Responses**

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/HealthResponse"
        }
      }
    },
    "description": "Successful Response"
  }
}
```
