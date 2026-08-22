import { motion } from "framer-motion";

const COHORT_COLOR = {
  hub: "#17140F",
  "in-target": "#3452D9",
  "out-of-target": "#DD6B2C",
  "never-shown": "#B7B0A0",
};

export default function AgentNode({ node, isSelected, onSelect }) {
  const color = COHORT_COLOR[node.cohort] ?? COHORT_COLOR["never-shown"];
  const isHub = node.kind === "hub";
  const baseRadius = isHub ? 7.5 : node.sharedDirectly ? 6.2 : 4.6;

  return (
    <motion.g
      initial={{ opacity: 0, scale: 0 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: "spring", stiffness: 260, damping: 20 }}
      style={{ transformOrigin: `${node.x}px ${node.y}px` }}
      onClick={() => node.personaId && onSelect(node.id)}
      className={node.personaId ? "cursor-pointer" : ""}
    >
      {isSelected && (
        <circle
          cx={node.x}
          cy={node.y}
          r={baseRadius + 5}
          fill="none"
          stroke={color}
          strokeWidth={1.4}
          opacity={0.5}
        />
      )}
      <circle cx={node.x} cy={node.y} r={baseRadius} fill={color} />
      {node.cohort !== "never-shown" && node.round === 1 && (
        <circle
          cx={node.x}
          cy={node.y}
          r={baseRadius + 2.2}
          fill="none"
          stroke={color}
          strokeWidth={1}
          opacity={0.35}
        />
      )}
    </motion.g>
  );
}
