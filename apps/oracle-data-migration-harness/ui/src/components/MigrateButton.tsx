export function MigrateButton({ onClick, disabled }: { onClick: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="px-6 py-3 rounded-lg bg-oracle-red text-white font-medium disabled:opacity-50"
    >
      Migrate
    </button>
  );
}
