# Frontend CSS Structure Map

## Component Hierarchy

```
App
├── .app (root container)
│   ├── .app.has-messages (when messages exist)
│   └── .app.has-messages.settled (after animation completes)
│
├── .welcome-message (initial state)
│   └── .welcome-logo
│
└── .chat-container
    ├── .chat-container.expanded (when messages exist)
    │
    ├── .messages-viewport (scrollable message area)
    │   ├── .message (base message style)
    │   │   ├── .user-message
    │   │   ├── .assistant-message
    │   │   │
    │   │   ├── .tool-calls-section
    │   │   │   ├── .tool-calls-header
    │   │   │   └── .tool-call-drawer
    │   │   │       ├── .tool-call-drawer-header
    │   │   │       │   ├── .tool-call-drawer-title
    │   │   │       │   │   ├── .tool-call-drawer-icon
    │   │   │       │   │   └── .tool-name
    │   │   │       │
    │   │   │       └── .tool-call-drawer-content
    │   │   │           ├── .tool-call-section
    │   │   │           │   ├── .tool-section-label
    │   │   │           │   ├── .tool-arguments-expanded
    │   │   │           │   │   └── .tool-arg
    │   │   │           │   │       ├── .arg-key
    │   │   │           │   │       └── .arg-value
    │   │   │           │   └── .tool-result
    │   │   │
    │   │   └── .message-content
    │   │       ├── (ReactMarkdown renders here)
    │   │       ├── p, ul, ol, li, code, pre, strong, a
    │   │       └── .typing (loading animation)
    │   │
    │   └── .message-ui (for iframes)
    │
    └── .composer (input form)
        ├── .composer-input
        └── .composer-send
```

## Dynamic Classes

### Conditional Classes (via template literals):
1. **`.app`** + `.has-messages` + `.settled`
   - Applied when: messages.length > 0 AND isSettled === true
   - Purpose: Trigger canvas expansion animation

2. **`.chat-container`** + `.expanded`
   - Applied when: messages.length > 0
   - Purpose: Expand chat canvas from center

3. **`.message`** + `.user-message` OR `.assistant-message`
   - Applied based on: message.role
   - Purpose: Style user vs assistant messages differently

## Key CSS Features

### 1. Liquid Glass Effect
- Backdrop filter blur
- Semi-transparent backgrounds
- Multiple layered borders with opacity

### 2. Animations
- `@keyframes expandCanvas` - chat container expansion
- `@keyframes messageSlideIn` - message entry animation
- `@keyframes typing` - loading dots animation

### 3. Scrollbar Customization
- Webkit scrollbar styling for `.messages-viewport`

## CSS Dependencies

### Global Styles
- `body` - background gradient
- `body.custom-bg` - when BACKGROUND_IMAGE env var is set
- `*` - reset/base styles

### External Dependencies
- ReactMarkdown - renders `.message-content` children (p, ul, li, code, pre)
- remarkGfm - GitHub Flavored Markdown support

## State Management

### React State → CSS Classes
1. `messages.length > 0` → `.has-messages`, `.expanded`
2. `isSettled` (800ms timer) → `.settled`
3. `isLoading` → `.typing` animation
4. `tool.result` → controls drawer expansion
5. `BACKGROUND_IMAGE` env → `.custom-bg` on body

## Potential Simplifications

### Over-specified Selectors
- Many hover states that may not be necessary
- Multiple pseudo-classes for each element
- Separate styling for scrollbar that could use defaults

### Unused Classes
Need to verify in CSS:
- Classes defined but not used in JSX
- Redundant media queries
- Duplicate style definitions

### Animation Complexity
- Multiple cubic-bezier easing functions
- Could potentially use CSS custom properties for theming
- Some animations might be overkill for demo app

## Next Steps
1. Identify unused CSS classes
2. Consolidate redundant styles
3. Simplify animations while keeping liquid glass effect
4. Remove unnecessary specificity
5. Test that all interactive states still work
