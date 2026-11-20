type EmptyStateProps = {
  title: string;
  description: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="card empty-state">
      <div className="empty-state-route" aria-hidden="true">
        <span className="route-line" />
        <span className="empty-state-route-dot" />
      </div>
      <h3 className="section-title">{title}</h3>
      <p className="section-subtitle">{description}</p>
    </div>
  );
}
