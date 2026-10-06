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
