type EmptyStateProps = {
  title: string;
  description: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="card">
      <h3 className="section-title">{title}</h3>
      <p className="section-subtitle">{description}</p>
    </div>
  );
}
