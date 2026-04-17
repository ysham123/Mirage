export const springs = {
  snappy: {
    type: "spring" as const,
    stiffness: 320,
    damping: 28,
    mass: 0.85,
  },
  soft: {
    type: "spring" as const,
    stiffness: 180,
    damping: 24,
    mass: 0.95,
  },
};

export const fadeUp = {
  hidden: { opacity: 0, y: 14 },
  visible: {
    opacity: 1,
    y: 0,
    transition: springs.soft,
  },
};
