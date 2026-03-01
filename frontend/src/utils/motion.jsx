import { motion, AnimatePresence } from "motion/react";
import { useLocation, Outlet } from "react-router-dom";

export const pageTransition = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: {
    type: "spring",
    stiffness: 260,
    damping: 28,
    mass: 0.8,
  },
};

export const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.05,
    },
  },
};

export const fadeInUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: {
    type: "spring",
    stiffness: 300,
    damping: 24,
  },
};

export const scaleIn = {
  initial: { opacity: 0, scale: 0.92 },
  animate: { opacity: 1, scale: 1 },
  transition: {
    type: "spring",
    stiffness: 400,
    damping: 25,
  },
};

export const cardHover = {
  whileHover: {
    y: -2,
    transition: { type: "spring", stiffness: 400, damping: 20 },
  },
  whileTap: { scale: 0.98 },
};

export const buttonSpring = {
  whileHover: {
    scale: 1.02,
    transition: { type: "spring", stiffness: 500, damping: 15 },
  },
  whileTap: { scale: 0.96 },
};

export function PageTransition({ children }) {
  return <motion.div {...pageTransition}>{children}</motion.div>;
}

export function StaggerList({ children, className }) {
  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className }) {
  return (
    <motion.div variants={fadeInUp} className={className}>
      {children}
    </motion.div>
  );
}

export { motion, AnimatePresence };
