export default function MessageBubble({ role, content }) {
  return (
    <div className={`message-row ${role}`}>
      {role === "assistant" && (
        <div className="avatar">🛣️</div>
      )}
      <div className={`bubble ${role}`}>{content}</div>
    </div>
  );
}
