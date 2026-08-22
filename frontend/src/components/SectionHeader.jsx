export default function SectionHeader({ number, title, caption }) {
  return (
    <div className="flex items-start justify-between px-4 pb-2 pt-5 sm:px-6">
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-semibold text-muted">{number}</span>
        <span className="text-[11px] font-bold uppercase tracking-widest text-ink">
          {title}
        </span>
      </div>
      {caption && (
        <p className="max-w-[65%] text-right text-[11px] leading-snug text-muted">
          {caption}
        </p>
      )}
    </div>
  );
}
