const ITEMS = [
  { type: "dot", color: "#3452D9", label: "in-target" },
  { type: "dot", color: "#DD6B2C", label: "out-of-target" },
  { type: "dot", color: "#B7B0A0", label: "never shown" },
  { type: "line", style: "solid", color: "#9A3B34", label: "shared directly" },
  { type: "line", style: "dashed", color: "#C9C2B1", label: "shown by algo" },
  { type: "icon", icon: "♥", label: "liked" },
  { type: "icon", icon: "◈", label: "commented" },
  { type: "icon", icon: "▲", label: "shared" },
];

export default function GraphLegend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line px-4 py-2 text-[10px] text-muted sm:px-6">
      {ITEMS.map((item) => (
        <span key={item.label} className="flex items-center gap-1.5">
          {item.type === "dot" && (
            <span
              className="inline-block h-[6px] w-[6px] rounded-full"
              style={{ backgroundColor: item.color }}
            />
          )}
          {item.type === "line" && (
            <svg width="14" height="6">
              <line
                x1="0"
                y1="3"
                x2="14"
                y2="3"
                stroke={item.color}
                strokeWidth="1.2"
                strokeDasharray={item.style === "dashed" ? "2,2" : undefined}
              />
            </svg>
          )}
          {item.type === "icon" && (
            <span className="text-[9px] leading-none">{item.icon}</span>
          )}
          {item.label}
        </span>
      ))}
    </div>
  );
}
