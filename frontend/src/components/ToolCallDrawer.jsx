import { useState } from 'react';
import PropTypes from 'prop-types';

/**
 * Collapsible drawer for displaying tool call details
 */
export function ToolCallDrawer({ tool }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isExecuting = !tool.result;

  const toggleExpanded = () => {
    if (tool.result) {
      setIsExpanded(!isExpanded);
    }
  };

  return (
    <div className="tool-call-drawer">
      <div
        className="tool-call-drawer-header"
        onClick={toggleExpanded}
        style={{ cursor: tool.result ? 'pointer' : 'default' }}
      >
        <div className="tool-call-drawer-title">
          {tool.result && (
            <span className="tool-call-drawer-icon">
              {isExpanded ? '▼' : '▶'}
            </span>
          )}
          <span className="tool-name">
            {isExecuting ? `Using ${tool.name}...` : `Used ${tool.name}`}
          </span>
        </div>
      </div>

      {isExpanded && tool.result && (
        <div className="tool-call-drawer-content">
          <div className="tool-call-section">
            <div className="tool-section-label">ARGUMENTS</div>
            <div className="tool-arguments-expanded">
              {tool.arguments &&
                Object.entries(tool.arguments).map(([key, value]) => (
                  <div key={key} className="tool-arg">
                    <span className="arg-key">{key}:</span>
                    <span className="arg-value">{JSON.stringify(value)}</span>
                  </div>
                ))}
            </div>
          </div>

          <div className="tool-call-section">
            <div className="tool-section-label">RESULT</div>
            <div className="tool-result">
              <pre>{JSON.stringify(tool.result, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

ToolCallDrawer.propTypes = {
  tool: PropTypes.shape({
    id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    arguments: PropTypes.object,
    result: PropTypes.any,
  }).isRequired,
};
