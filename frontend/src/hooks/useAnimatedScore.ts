/**
 * Animated Score Hook
 * 
 * Provides spring-animated numeric values for smooth score transitions.
 * Used for TCRTE coverage bars and overall score counter.
 */

import { useSpring, useMotionValue, animate } from 'framer-motion';
import { useEffect } from 'react';
import { SCORE_SPRING_CONFIG } from '@/constants';

/**
 * Hook for spring-animated score values.
 * 
 * Returns a motion value that smoothly animates from the previous
 * value to the new target value using spring physics.
 * 
 * Usage:
 * ```tsx
 * const animatedScore = useAnimatedScore(75);
 * 
 * return (
 *   <motion.div style={{ width: animatedScore }}>
 *     {animatedScore.get()}
 *   </motion.div>
 * );
 * ```
 */
export function useAnimatedScore(targetValue: number) {
  const motionValue = useMotionValue(0);

  useEffect(() => {
    const controls = animate(motionValue, targetValue, {
      type: 'spring',
      ...SCORE_SPRING_CONFIG,
    });

    return () => controls.stop();
  }, [targetValue, motionValue]);

  return motionValue;
}

/**
 * Hook for spring-animated percentage width (for progress bars).
 * 
 * Returns a spring value representing a percentage (0-100).
 */
export function useAnimatedPercentage(targetPercentage: number) {
  const spring = useSpring(0, SCORE_SPRING_CONFIG);

  useEffect(() => {
    spring.set(targetPercentage);
  }, [targetPercentage, spring]);

  return spring;
}

/**
 * Hook for counting up to a target number (for display).
 * 
 * Returns a motion value that counts up from 0 to the target.
 * Use with useTransform or subscribe to get the current integer value.
 */
export function useCountUp(targetValue: number, delay: number = 0) {
  const motionValue = useMotionValue(0);

  useEffect(() => {
    const timeout = setTimeout(() => {
      const controls = animate(motionValue, targetValue, {
        duration: 0.8,
        ease: [0.25, 0.1, 0.25, 1],
      });

      return () => controls.stop();
    }, delay);

    return () => clearTimeout(timeout);
  }, [targetValue, delay, motionValue]);

  return motionValue;
}
