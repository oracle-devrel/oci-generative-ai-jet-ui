export interface Product {
  id: string;
  title: string;
  description: string;
  image: string;
  price: number;
  category: string;
  specification?: string; // made optional if not always present
  text?: string;          // made optional if not always present
}

export const sampleProducts: Product[] = [
  {
    id: "prod-10001",
    category: "Electronics | Computers & Accessories | Computer Components | Memory",
    description: "High-performance DDR4 memory module designed for gaming and professional applications. Delivers exceptional speed and reliability for demanding tasks.",
    image: "https://images.pexels.com/photos/163100/circuit-circuit-board-resistor-computer-163100.jpeg?auto=compress&cs=tinysrgb&w=500",
    price: 89.99,
    specification: "ProductDimensions: 5.3 x 1.2 x 0.3 inches | ItemWeight: 1.6 ounces | Capacity: 16GB | Speed: 3200MHz",
    text: "Corsair Vengeance LPX 16GB DDR4 DRAM 3200MHz Memory Module - High-performance memory designed for high-performance overclocking. The heat spreader is made of pure aluminum for faster heat dissipation.",
    title: "Corsair Vengeance LPX 16GB DDR4 DRAM 3200MHz Memory Module"
  },
  {
    id: "prod-10002",
    category: "Toys & Games | Hobbies | Remote & App Controlled Vehicles & Parts | Remote & App Controlled Vehicles | Quadcopters & Multirotors",
    description: "FLY IN STYLE: Show off your own unique style with Mighty Skins for your Parrot Anafi Drone Don't like the Geometric Rave skin We have hundreds of designs to choose from, so your Parrot Anafi Drone will be as unique as you are.",
    image: "https://images.pexels.com/photos/2049422/pexels-photo-2049422.jpeg?auto=compress&cs=tinysrgb&w=500",
    price: 24.99,
    specification: "ProductDimensions: 14x0.1x12inches | ItemWeight: 0.16ounces | ShippingWeight: 0.96ounces",
    text: "MightySkins Skin Compatible with Parrot Anafi Drone - Geometric Rave | Protective, Durable, and Unique Vinyl Decal wrap Cover | Easy to Apply, Remove, and Change Styles | Made in The USA",
    title: "MightySkins Skin Compatible with Parrot Anafi Drone - Geometric Rave"
  },
  {
    id: "prod-10003",
    category: "Home & Kitchen | Kitchen & Dining | Small Appliances | Coffee Machines",
    description: "Professional-grade espresso machine with built-in grinder. Perfect for coffee enthusiasts who demand café-quality beverages at home.",
    image: "https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=500",
    price: 299.99,
    specification: "ProductDimensions: 15 x 12 x 14 inches | ItemWeight: 18 pounds | Capacity: 1.8L | Power: 1350W",
    text: "Breville Barista Express Espresso Machine - Dose, grind, and extract with one touch. The integrated conical burr grinder grinds on demand to deliver the right amount of freshly ground coffee.",
    title: "Breville Barista Express Espresso Machine"
  },
  {
    id: "prod-10004",
    category: "Sports & Outdoors | Exercise & Fitness | Strength Training | Free Weights",
    description: "Adjustable dumbbells that replace an entire rack of weights. Perfect for home gyms with limited space but unlimited ambition.",
    image: "https://images.pexels.com/photos/1552252/pexels-photo-1552252.jpeg?auto=compress&cs=tinysrgb&w=500",
    price: 1000,
    specification: "ProductDimensions: 17.5 x 8 x 9 inches | ItemWeight: 52.5 pounds | AdjustableRange: 5-50lbs | Material: Cast Iron",
    text: "Bowflex SelectTech Adjustable Dumbbells - Replace 15 sets of weights with just one pair of dumbbells. Adjusts from 5 to 50 pounds with the turn of a dial.",
    title: "Bowflex SelectTech Adjustable Dumbbells"
  },
  {
    id: "prod-10005",
    category: "Books | Science & Math | Mathematics | Applied | Statistics",
    description: "Comprehensive guide to statistical analysis and data science. Perfect for students, researchers, and professionals working with data.",
    image: "https://images.pexels.com/photos/159775/library-book-bookshelf-read-159775.jpeg?auto=compress&cs=tinysrgb&w=500",
    price: 79.99,
    specification: "ProductDimensions: 9.2 x 7.5 x 1.8 inches | ItemWeight: 2.4 pounds | Pages: 832 | Publisher: Academic Press",
    text: "The Elements of Statistical Learning: Data Mining, Inference, and Prediction - During the past decade there has been an explosion in computation and information technology.",
    title: "The Elements of Statistical Learning: Data Mining, Inference, and Prediction"
  },
  {
    id: "prod-10006",
    category: "Fashion | Women | Clothing | Activewear | Tops",
    description: "Ultra-soft, moisture-wicking fabric keeps you comfortable during workouts. Designed with a flattering fit that moves with you.",
    image: "https://images.pexels.com/photos/794062/pexels-photo-794062.jpeg?auto=compress&cs=tinysrgb&w=500",
    price: 34.99,
    specification: "ProductDimensions: Various sizes | Material: 87% Polyester, 13% Elastane | Features: Moisture-wicking, 4-way stretch",
    text: "Lululemon Align Tank Top - Designed for yoga and low-impact workouts. Made with Nulu fabric that feels weightless and buttery-soft.",
    title: "Lululemon Align Tank Top"
  },
  {
    id: "prod-10007",
    category: "Automotive | Car Care | Exterior Care | Car Wash & Shampoo",
    description: "Professional-grade car wash soap that safely removes dirt and grime while protecting your vehicle's finish.",
    image: "https://images.pexels.com/photos/97075/pexels-photo-97075.jpeg?auto=compress&cs=tinysrgb&w=500",
    price: 19.99,
    specification: "ProductDimensions: 8 x 3 x 10 inches | ItemWeight: 2 pounds | Volume: 64 fl oz | pH balanced",
    text: "Chemical Guys Mr. Pink Super Suds Car Wash Soap - Safe for all exterior automotive surfaces including paint, clear coat, polished metals, glass, and plastic trim.",
    title: "Chemical Guys Mr. Pink Super Suds Car Wash Soap"
  },
  {
    id: "prod-10008",
    category: "Beauty & Personal Care | Skin Care | Face | Moisturizers",
    description: "Lightweight, non-greasy moisturizer with SPF 30 protection. Perfect for daily use to maintain healthy, protected skin.",
    image: "https://images.pexels.com/photos/3762879/pexels-photo-3762879.jpeg?auto=compress&cs=tinysrgb&w=500",
    price: 24.99,
    specification: "ProductDimensions: 6.5 x 2 x 1.5 inches | ItemWeight: 1.7 ounces | Volume: 1.7 fl oz | SPF: 30",
    text: "CeraVe Daily Facial Moisturizing Lotion SPF 30 - Developed with dermatologists, this face moisturizer has 3 essential ceramides that work together to lock in skin's moisture.",
    title: "CeraVe Daily Facial Moisturizing Lotion SPF 30"
  },
  {
    id: "prod-10009",
    category: "Pet Supplies | Dogs | Toys | Rope & Tug Toys",
    description: "Durable rope toy designed for aggressive chewers. Made from natural cotton fibers that help clean teeth and massage gums.",
    image: "https://images.pexels.com/photos/1254140/pexels-photo-1254140.jpeg?auto=compress&cs=tinysrgb&w=500",
    price: 12.99,
    specification: "ProductDimensions: 12 x 3 x 2 inches | ItemWeight: 8 ounces | Material: 100% Natural Cotton | Size: Large",
    text: "Mammoth Flossy Chews Cottonblend Color 3-Knot Rope Tug - Made from premium cotton-poly fibers. Toss, tug, and fetch. Great for interactive play.",
    title: "Mammoth Flossy Chews Cottonblend Color 3-Knot Rope Tug"
  },
  {
    id: "prod-10010",
    category: "Office Products | Office & School Supplies | Desk Accessories & Workspace Organizers | Desk Organizers",
    description: "Bamboo desk organizer with multiple compartments. Eco-friendly solution to keep your workspace clean and organized.",
    image: "https://images.pexels.com/photos/1181403/pexels-photo-1181403.jpeg?auto=compress&cs=tinysrgb&w=500",
    price: 39.99,
    specification: "ProductDimensions: 11.8 x 8.2 x 4.3 inches | ItemWeight: 2.2 pounds | Material: 100% Bamboo | Compartments: 7",
    text: "Bamboo Desk Organizer with Adjustable Drawer - Made from sustainable bamboo wood. Multiple compartments for pens, pencils, paper clips, and more.",
    title: "Bamboo Desk Organizer with Adjustable Drawer"
  },
  {
    id: "prod-10011",
    category: "Health & Household | Vitamins & Supplements | Vitamins | Vitamin D",
    description: "High-potency Vitamin D3 supplement for bone health and immune system support. Third-party tested for purity and potency.",
    image: "https://images.pexels.com/photos/40751/vitamin-medical-pills-medication-40751.jpeg?auto=compress&cs=tinysrgb&w=500",
    price: 16.99,
    specification: "ProductDimensions: 4.5 x 2.4 x 2.4 inches | ItemWeight: 3.2 ounces | Servings: 365 | Strength: 5000 IU",
    text: "Nature Made Vitamin D3 5000 IU Softgels - Helps support bone, teeth, muscle and immune health. #1 Pharmacist Recommended Vitamin D Brand.",
    title: "Nature Made Vitamin D3 5000 IU Softgels"
  },
  {
    id: "prod-10012",
    category: "Tools & Home Improvement | Hardware | Cabinet Hardware | Knobs",
    description: "Modern brushed gold cabinet knobs that add elegance to any kitchen or bathroom. Easy to install with included screws.",
    image: "https://images.pexels.com/photos/1643383/pexels-photo-1643383.jpeg?auto=compress&cs=tinysrgb&w=500",
    price: 2.99,
    specification: "ProductDimensions: 1.25 x 1.25 x 1 inches | ItemWeight: 1.6 ounces | Material: Brushed Brass | Pack: Single",
    text: "Brushed Gold Cabinet Knobs - Premium quality cabinet hardware with a beautiful brushed gold finish. Adds a touch of luxury to any space.",
    title: "Brushed Gold Cabinet Knobs"
  }
];

export const getRandomProducts = (count: number = 8): Product[] => {
  const shuffled = [...sampleProducts].sort(() => 0.5 - Math.random());
  return shuffled.slice(0, count);
};

export const getUniqueCategories = (): string[] => {
  const categories = new Set<string>();
  sampleProducts.forEach(product => {
    const categoryParts = product.category.split(' | ');
    categoryParts.forEach(part => categories.add(part.trim()));
  });
  return Array.from(categories).sort();
};

export const getPriceRange = (): { min: number; max: number } => {
  const prices = sampleProducts.map(p => p.price);
  return {
    min: Math.min(...prices),
    max: Math.max(...prices)
  };
};