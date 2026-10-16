# MCP Tools

> Generated from the registered MCP tools. Do not edit manually.

## Tools

### `content.create-audio`

Create MP3 audio from text content.

**Input schema**

```json
{
  "properties": {
    "content": {
      "title": "Content",
      "type": "string"
    },
    "output_file": {
      "title": "Output File",
      "type": "string"
    }
  },
  "required": [
    "content",
    "output_file"
  ],
  "title": "create_audioArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "properties": {
    "result": {
      "title": "Result",
      "type": "null"
    }
  },
  "required": [
    "result"
  ],
  "title": "create_audioOutput",
  "type": "object"
}
```

### `file.copy`

**Input schema**

```json
{
  "properties": {
    "destination": {
      "title": "Destination",
      "type": "string"
    },
    "source": {
      "title": "Source",
      "type": "string"
    }
  },
  "required": [
    "source",
    "destination"
  ],
  "title": "copyArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "properties": {
    "result": {
      "title": "Result",
      "type": "null"
    }
  },
  "required": [
    "result"
  ],
  "title": "copyOutput",
  "type": "object"
}
```

### `mail.create_categories`

**Input schema**

```json
{
  "properties": {
    "categories": {
      "items": {
        "type": "string"
      },
      "title": "Categories",
      "type": "array"
    }
  },
  "required": [
    "categories"
  ],
  "title": "create_categoriesArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "properties": {
    "result": {
      "title": "Result",
      "type": "null"
    }
  },
  "required": [
    "result"
  ],
  "title": "create_categoriesOutput",
  "type": "object"
}
```

### `mail.get_attachment`

Get one mail attachment as Base64-encoded binary content.

**Input schema**

```json
{
  "properties": {
    "attachment_id": {
      "title": "Attachment Id",
      "type": "string"
    },
    "message_id": {
      "title": "Message Id",
      "type": "string"
    }
  },
  "required": [
    "message_id",
    "attachment_id"
  ],
  "title": "get_attachmentArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "properties": {
    "content_base64": {
      "title": "Content Base64",
      "type": "string"
    },
    "file_name": {
      "title": "File Name",
      "type": "string"
    },
    "mime_type": {
      "title": "Mime Type",
      "type": "string"
    }
  },
  "required": [
    "file_name",
    "mime_type",
    "content_base64"
  ],
  "title": "MailAttachmentResponse",
  "type": "object"
}
```

### `mail.get_categories`

**Input schema**

```json
{
  "properties": {},
  "title": "get_categoriesArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "properties": {
    "result": {
      "items": {
        "type": "string"
      },
      "title": "Result",
      "type": "array"
    }
  },
  "required": [
    "result"
  ],
  "title": "get_categoriesOutput",
  "type": "object"
}
```

### `mail.get_mail`

Get one mail with its preferred body, as LLM-friendly plaintext by default.

**Input schema**

```json
{
  "properties": {
    "as_text": {
      "default": true,
      "title": "As Text",
      "type": "boolean"
    },
    "message_id": {
      "title": "Message Id",
      "type": "string"
    }
  },
  "required": [
    "message_id"
  ],
  "title": "get_mailArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "$defs": {
    "MailAttachment": {
      "properties": {
        "id": {
          "title": "Id",
          "type": "string"
        },
        "mime_type": {
          "title": "Mime Type",
          "type": "string"
        },
        "name": {
          "title": "Name",
          "type": "string"
        }
      },
      "required": [
        "name",
        "id",
        "mime_type"
      ],
      "title": "MailAttachment",
      "type": "object"
    },
    "MailSender": {
      "properties": {
        "email_address": {
          "title": "Email Address",
          "type": "string"
        },
        "name": {
          "title": "Name",
          "type": "string"
        }
      },
      "required": [
        "name",
        "email_address"
      ],
      "title": "MailSender",
      "type": "object"
    }
  },
  "properties": {
    "attachments": {
      "items": {
        "$ref": "#/$defs/MailAttachment"
      },
      "title": "Attachments",
      "type": "array"
    },
    "body_content": {
      "title": "Body Content",
      "type": "string"
    },
    "body_mime_type": {
      "title": "Body Mime Type",
      "type": "string"
    },
    "internal_date": {
      "format": "date-time",
      "title": "Internal Date",
      "type": "string"
    },
    "is_read": {
      "title": "Is Read",
      "type": "boolean"
    },
    "message_id": {
      "title": "Message Id",
      "type": "string"
    },
    "sender": {
      "$ref": "#/$defs/MailSender"
    },
    "subject": {
      "title": "Subject",
      "type": "string"
    },
    "thread_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Thread Id"
    }
  },
  "required": [
    "message_id",
    "is_read",
    "internal_date",
    "subject",
    "sender",
    "thread_id",
    "body_mime_type",
    "body_content",
    "attachments"
  ],
  "title": "Mail",
  "type": "object"
}
```

### `mail.get_messages`

**Input schema**

```json
{
  "properties": {
    "before": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Before"
    },
    "category": {
      "title": "Category",
      "type": "string"
    },
    "since": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Since"
    }
  },
  "required": [
    "category"
  ],
  "title": "get_messagesArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "$defs": {
    "MailMessage": {
      "properties": {
        "internal_date": {
          "format": "date-time",
          "title": "Internal Date",
          "type": "string"
        },
        "is_read": {
          "title": "Is Read",
          "type": "boolean"
        },
        "message_id": {
          "title": "Message Id",
          "type": "string"
        },
        "sender": {
          "title": "Sender",
          "type": "string"
        },
        "subject": {
          "title": "Subject",
          "type": "string"
        },
        "thread_id": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Thread Id"
        }
      },
      "required": [
        "message_id",
        "thread_id",
        "internal_date",
        "subject",
        "sender",
        "is_read"
      ],
      "title": "MailMessage",
      "type": "object"
    }
  },
  "properties": {
    "result": {
      "items": {
        "$ref": "#/$defs/MailMessage"
      },
      "title": "Result",
      "type": "array"
    }
  },
  "required": [
    "result"
  ],
  "title": "get_messagesOutput",
  "type": "object"
}
```

### `mail.get_messages_by_thread`

**Input schema**

```json
{
  "properties": {
    "thread_id": {
      "title": "Thread Id",
      "type": "string"
    }
  },
  "required": [
    "thread_id"
  ],
  "title": "get_messages_by_threadArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "$defs": {
    "MailMessage": {
      "properties": {
        "internal_date": {
          "format": "date-time",
          "title": "Internal Date",
          "type": "string"
        },
        "is_read": {
          "title": "Is Read",
          "type": "boolean"
        },
        "message_id": {
          "title": "Message Id",
          "type": "string"
        },
        "sender": {
          "title": "Sender",
          "type": "string"
        },
        "subject": {
          "title": "Subject",
          "type": "string"
        },
        "thread_id": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Thread Id"
        }
      },
      "required": [
        "message_id",
        "thread_id",
        "internal_date",
        "subject",
        "sender",
        "is_read"
      ],
      "title": "MailMessage",
      "type": "object"
    }
  },
  "properties": {
    "result": {
      "items": {
        "$ref": "#/$defs/MailMessage"
      },
      "title": "Result",
      "type": "array"
    }
  },
  "required": [
    "result"
  ],
  "title": "get_messages_by_threadOutput",
  "type": "object"
}
```

### `mail.get_provider_stats`

**Input schema**

```json
{
  "properties": {},
  "title": "get_provider_statsArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "properties": {
    "all_messages_count": {
      "title": "All Messages Count",
      "type": "integer"
    },
    "inbox_messages_count": {
      "title": "Inbox Messages Count",
      "type": "integer"
    },
    "inbox_unread_count": {
      "title": "Inbox Unread Count",
      "type": "integer"
    },
    "newest_message_date": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Newest Message Date"
    },
    "oldest_message_date": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Oldest Message Date"
    }
  },
  "required": [
    "all_messages_count",
    "inbox_messages_count",
    "inbox_unread_count",
    "oldest_message_date",
    "newest_message_date"
  ],
  "title": "MailProviderStats",
  "type": "object"
}
```

### `mail.set_categories`

**Input schema**

```json
{
  "properties": {
    "archive": {
      "default": false,
      "title": "Archive",
      "type": "boolean"
    },
    "categories": {
      "items": {
        "type": "string"
      },
      "title": "Categories",
      "type": "array"
    },
    "mark_unread": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Mark Unread"
    },
    "message_id": {
      "title": "Message Id",
      "type": "string"
    }
  },
  "required": [
    "message_id",
    "categories"
  ],
  "title": "set_categoriesArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "properties": {
    "result": {
      "title": "Result",
      "type": "null"
    }
  },
  "required": [
    "result"
  ],
  "title": "set_categoriesOutput",
  "type": "object"
}
```

### `mail.set_provider`

**Input schema**

```json
{
  "properties": {
    "provider": {
      "enum": [
        "gmail",
        "mailbox"
      ],
      "title": "Provider",
      "type": "string"
    }
  },
  "required": [
    "provider"
  ],
  "title": "set_providerArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "properties": {
    "result": {
      "title": "Result",
      "type": "null"
    }
  },
  "required": [
    "result"
  ],
  "title": "set_providerOutput",
  "type": "object"
}
```

### `mail.unset_categories`

**Input schema**

```json
{
  "properties": {
    "categories": {
      "items": {
        "type": "string"
      },
      "title": "Categories",
      "type": "array"
    },
    "message_id": {
      "title": "Message Id",
      "type": "string"
    }
  },
  "required": [
    "message_id",
    "categories"
  ],
  "title": "unset_categoriesArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "properties": {
    "result": {
      "title": "Result",
      "type": "null"
    }
  },
  "required": [
    "result"
  ],
  "title": "unset_categoriesOutput",
  "type": "object"
}
```

### `music.play_tracks`

Play the supplied track IDs in their given order.

**Input schema**

```json
{
  "properties": {
    "track_ids": {
      "items": {
        "type": "integer"
      },
      "title": "Track Ids",
      "type": "array"
    }
  },
  "required": [
    "track_ids"
  ],
  "title": "play_tracksArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "properties": {
    "result": {
      "title": "Result",
      "type": "null"
    }
  },
  "required": [
    "result"
  ],
  "title": "play_tracksOutput",
  "type": "object"
}
```

### `web.get-content`

Fetch a URL and return its LLM-ready textual content.

**Input schema**

```json
{
  "properties": {
    "url": {
      "title": "Url",
      "type": "string"
    }
  },
  "required": [
    "url"
  ],
  "title": "get_contentArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "additionalProperties": {
    "anyOf": [
      {
        "type": "string"
      },
      {
        "type": "boolean"
      }
    ]
  },
  "title": "get_contentDictOutput",
  "type": "object"
}
```

### `web.search`

Search DuckDuckGo for the supplied query.

**Input schema**

```json
{
  "properties": {
    "query": {
      "title": "Query",
      "type": "string"
    }
  },
  "required": [
    "query"
  ],
  "title": "searchArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "properties": {
    "result": {
      "items": {
        "additionalProperties": {
          "type": "string"
        },
        "type": "object"
      },
      "title": "Result",
      "type": "array"
    }
  },
  "required": [
    "result"
  ],
  "title": "searchOutput",
  "type": "object"
}
```

### `workflow.execute`

Execute one registered workflow with a JSON payload.

**Input schema**

```json
{
  "$defs": {
    "JsonValue": {}
  },
  "properties": {
    "payload": {
      "$ref": "#/$defs/JsonValue"
    },
    "workflow_key": {
      "title": "Workflow Key",
      "type": "string"
    }
  },
  "required": [
    "workflow_key",
    "payload"
  ],
  "title": "executeArguments",
  "type": "object"
}
```

**Output schema**

```json
{
  "additionalProperties": {
    "type": "integer"
  },
  "title": "executeDictOutput",
  "type": "object"
}
```
