/**
 * Roadmap artifact data contract.
 *
 * Mirrors RoadmapContent Python Pydantic model (common/contracts/roadmap.py).
 * Used when artifact_type == "roadmap".
 */

import type { ContentComponent } from "./components.js";

export interface StatCard {
  label: string;
  value: string;
  variant?: "target" | "now" | "default";
}

export interface NavItem {
  label: string;
  href: string;
  group?: string;
}

export interface LegendItem {
  color: string;
  label: string;
}

export interface RoadmapSidebar {
  title: string;
  subtitle: string;
  stats?: StatCard[];
  nav?: NavItem[];
  legend?: LegendItem[];
}

export interface RoadmapHero {
  eyebrow?: string;
  title: string;
  lede?: string;
  stamp?: string;
  stats?: StatCard[];
}

export interface RoadmapSection {
  id: string;
  title: string;
  subtitle?: string;
  tag_num?: string;
  components?: ContentComponent[];
}

export interface RoadmapData {
  title: string;
  theme?: string;
  hero: RoadmapHero;
  sections?: RoadmapSection[];
  sidebar: RoadmapSidebar;
  accessibility?: { language?: string };
}
