import { Product } from "./sampleProducts";

export interface UserPurchase {
  id: string;
  productId: string;
  purchaseDate: string;
  quantity: number;
}

export type RecommendedProduct = Product;
// Mock user purchase history
export const userPurchaseHistory: UserPurchase[] = [
  {
    id: "purchase-1",
    productId: "prod-10001",
    purchaseDate: "2024-12-15",
    quantity: 1
  },
  {
    id: "purchase-2",
    productId: "prod-10003",
    purchaseDate: "2024-12-10",
    quantity: 1
  },
  {
    id: "purchase-3",
    productId: "prod-10006",
    purchaseDate: "2024-12-05",
    quantity: 2
  }
];

