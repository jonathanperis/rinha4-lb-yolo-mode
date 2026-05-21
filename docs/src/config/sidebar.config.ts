export const SECTION_CATEGORIES = [
  { label: '', ids: ['home'] },
  { label: 'System', ids: ['challenge', 'architecture', 'contracts'] },
  { label: 'Operate', ids: ['getting-started', 'performance', 'comparison'] },
] as const;

export const SECTION_ORDER = SECTION_CATEGORIES.flatMap(({ ids }) => ids);
