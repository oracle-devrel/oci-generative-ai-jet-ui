const DEFAULT_GENDERS = [
  'Men',
  'Women',
  'Unisex',
  'Boys',
  'Girls',
];

const DEFAULT_MASTER_CATEGORIES = [
  'Apparel',
  'Footwear',
  'Accessories',
  'Personal Care',
  'Sporting Goods',
];

export const vectorDB = {
  getFilterOptions(): { genders: string[]; masterCategories: string[] } {
    return {
      genders: DEFAULT_GENDERS,
      masterCategories: DEFAULT_MASTER_CATEGORIES,
    };
  },
};
