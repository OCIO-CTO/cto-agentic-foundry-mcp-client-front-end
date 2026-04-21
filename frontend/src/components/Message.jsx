import PropTypes from 'prop-types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ToolCallDrawer } from './ToolCallDrawer';
import { TextToSpeech } from './TextToSpeech';
import { UI_SETTINGS, MESSAGE_ROLES } from '../config/constants';

/**
 * Message component for displaying user and assistant messages
 */
export function Message({ message }) {
  const { id, role, content, toolCalls, ui } = message;

  return (
    <div className={`message ${role}-message`}>
      {toolCalls && toolCalls.length > 0 && (
        <div className="tool-calls-section">
          <div className="tool-calls-header">Tool Execution</div>
          {toolCalls.map((tool) => (
            <ToolCallDrawer key={tool.id} tool={tool} />
          ))}
        </div>
      )}

      <div className="message-content-wrapper">
        <div className="message-content">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ node, ...props }) => (
                <a {...props} target="_blank" rel="noopener noreferrer" />
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        </div>

        {role === MESSAGE_ROLES.ASSISTANT && content && (
          <div className="message-actions">
            <TextToSpeech text={content} />
          </div>
        )}
      </div>

      {ui && (
        <div className="message-ui">
          {(Array.isArray(ui) ? ui : [ui]).map((uiComponent, idx) =>
            uiComponent.type === 'iframe' ? (
              <iframe
                key={idx}
                src={uiComponent.url}
                style={{
                  width: '100%',
                  height: uiComponent.height || UI_SETTINGS.IFRAME_DEFAULT_HEIGHT,
                  border: 'none',
                  borderRadius: '8px',
                  marginTop: idx === 0 ? '12px' : '8px',
                  marginBottom: '8px',
                }}
                title={`MCP UI Resource: ${uiComponent.resourceUri || idx + 1}`}
                sandbox={UI_SETTINGS.IFRAME_SANDBOX}
              />
            ) : null
          )}
        </div>
      )}
    </div>
  );
}

Message.propTypes = {
  message: PropTypes.shape({
    id: PropTypes.number.isRequired,
    role: PropTypes.string.isRequired,
    content: PropTypes.string.isRequired,
    toolCalls: PropTypes.array,
    ui: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
  }).isRequired,
};
