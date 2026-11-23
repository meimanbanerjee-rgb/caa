// frontend/src/types/theme.ts
// Theme and sustainable color palette configuration for Infosys AI.

export type ThemeId = 'solar' | 'infosys' | 'emerald' | 'amethyst';

export interface ThemeConfig {
  id: ThemeId;
  name: string;
  description: string;
  primary: string;       // HEX color
  secondary: string;     // HEX color
  accentBg: string;      // Tailwind class for background tint
  accentBorder: string;  // Tailwind class for border tint
  accentText: string;    // Tailwind class for text
  glowColor: string;     // RGBA glow string
  sparklineStroke: string;
}

export const THEMES: Record<ThemeId, ThemeConfig> = {
  solar: {
    id: 'solar',
    name: 'Solar Obsidian',
    description: 'Warm solar amber and deep charcoal contrast (screenshot style)',
    primary: '#f97316',
    secondary: '#f59e0b',
    accentBg: 'bg-orange-500/15',
    accentBorder: 'border-orange-500/30',
    accentText: 'text-orange-400',
    glowColor: 'rgba(249, 115, 22, 0.25)',
    sparklineStroke: '#f97316',
  },
  infosys: {
    id: 'infosys',
    name: 'Infosys Blue',
    description: 'Iconic digital blue and electric sapphire',
    primary: '#0ea5e9',
    secondary: '#38bdf8',
    accentBg: 'bg-sky-500/15',
    accentBorder: 'border-sky-500/30',
    accentText: 'text-sky-400',
    glowColor: 'rgba(14, 165, 233, 0.25)',
    sparklineStroke: '#0ea5e9',
  },
  emerald: {
    id: 'emerald',
    name: 'Sustainable Eco',
    description: 'Clean eco-green and fresh mint for sustainable analytics',
    primary: '#10b981',
    secondary: '#06b6d4',
    accentBg: 'bg-emerald-500/15',
    accentBorder: 'border-emerald-500/30',
    accentText: 'text-emerald-400',
    glowColor: 'rgba(16, 185, 129, 0.25)',
    sparklineStroke: '#10b981',
  },
  amethyst: {
    id: 'amethyst',
    name: 'Royal Amethyst',
    description: 'Vibrant violet and magenta night palette',
    primary: '#a855f7',
    secondary: '#ec4899',
    accentBg: 'bg-purple-500/15',
    accentBorder: 'border-purple-500/30',
    accentText: 'text-purple-400',
    glowColor: 'rgba(168, 85, 247, 0.25)',
    sparklineStroke: '#a855f7',
  },
};
