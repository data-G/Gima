type SafetyNoticeProps = {
  compact?: boolean;
};

export function SafetyNotice({ compact = false }: SafetyNoticeProps) {
  return (
    <div className={`rounded-md border border-red-200 bg-red-50 text-red-900 ${compact ? "p-3 text-sm" : "p-4 text-sm"}`}>
      <strong>Paper trading only.</strong> Gima Safe Trading Agent provides risk-controlled decision support. Trading involves risk, human approval is required, and past performance does not guarantee future results. Capital protection first.
    </div>
  );
}
