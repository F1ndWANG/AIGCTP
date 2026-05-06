// ===== Auth =====
export interface User {
  id: number;
  username: string;
  display_name: string;
  avatar_url?: string;
  preferences?: Record<string, unknown>;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ===== Chat =====
export interface ChatSession {
  session_id: string;
  title: string;
  message_count: number;
  last_preview: string;
  updated_at: string;
}

export interface ChatSessionDetail {
  session_id: string;
  title: string;
  messages: Message[];
  context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  id?: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  travel_plan_id?: number;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  travel_plan?: TravelPlanResponse;
  products?: ProductListItem[];
  restaurants?: Restaurant[];
  restaurant_recommendation_id?: number;
  restaurant_recommendation?: SavedRestaurantRecommendation;
  diet_plan?: Record<string, unknown>;
  cart_items?: Array<Record<string, unknown>>;
  artifacts?: Record<string, unknown>;
}

// ===== Travel Plan =====
export interface TravelPlanItineraryDay {
  day: number;
  theme: string;
  weather?: {
    condition?: string;
    temp_min?: string;
    temp_max?: string;
    temp_low?: string;
    temp_high?: string;
    temperature?: string;
  };
  meals?: Array<{
    type: string;
    recommendation: string;
    restaurant?: string;
    description?: string;
  }>;
  activities?: Array<{
    time: string;
    poi: string;
    duration?: string;
    description?: string;
    tips?: string;
  }>;
  shopping?: Array<{
    product_id: number;
    product_name: string;
    price: number;
    reason: string;
  }>;
  hotel?: {
    name: string;
    price_level?: string;
    reason?: string;
    tips?: string;
  };
  transport_tips?: string;
}

export interface TravelPlanItinerary {
  destination: string;
  days: number;
  theme?: string;
  day_by_day: TravelPlanItineraryDay[];
  budget_estimate?: {
    total: string;
    breakdown?: Record<string, string>;
  };
  tips?: string[];
}

export interface TravelPlanResponse {
  id: number;
  destination: string;
  days: number;
  start_date?: string;
  end_date?: string;
  budget?: number;
  people_count: number;
  preferences: Record<string, unknown>;
  itinerary?: TravelPlanItinerary;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface TravelPlanListItem {
  id: number;
  destination: string;
  days: number;
  status: string;
  created_at: string;
}

// ===== Route Planning =====
export interface RouteRequest {
  destination_name: string;
  destination_lat?: number;
  destination_lng?: number;
  origin_lat: number;
  origin_lng: number;
  city?: string;
  mode: "transit" | "driving" | "walking";
}

export interface RouteStep {
  instruction: string;
  distance: string;
  duration: string;
}

export interface RouteResponse {
  distance: string;
  duration: string;
  mode: string;
  steps: RouteStep[];
  destination_name: string;
  maps_url: string;
  origin_lat: number;
  origin_lng: number;
  destination_lat: number;
  destination_lng: number;
}

// ===== Diet & Health =====
export interface HealthProfile {
  id?: number;
  height?: number;
  weight?: number;
  age?: number;
  gender?: string;
  allergies: string[];
  chronic_conditions: string[];
  diet_goals: string[];
  dietary_restrictions: string[];
}

export interface FoodItem {
  name: string;
  amount: string;
  calories?: number;
  protein?: number;
  carbs?: number;
  fat?: number;
}

export interface MealRecord {
  id?: number;
  date: string;
  meal_type: "breakfast" | "lunch" | "dinner" | "snack";
  foods: FoodItem[];
  total_nutrition?: {
    calories: number;
    protein: number;
    carbs: number;
    fat: number;
  };
  notes?: string;
}

export interface MealSummary {
  records: MealRecord[];
  total_calories: number;
  total_protein: number;
  total_carbs: number;
  total_fat: number;
}

export interface DietPlan {
  id: number;
  title: string;
  duration_days: number;
  meals?: {
    day_by_day: Array<{
      day: number;
      meals: Array<{
        meal_type: string;
        foods: FoodItem[];
      }>;
    }>;
  };
  total_nutrition?: {
    calories: number;
    protein: number;
    carbs: number;
    fat: number;
  };
  tips?: string[];
  status: string;
  activated_at?: string;
  created_at: string;
}

export interface DietPlanListItem {
  id: number;
  title: string;
  duration_days: number;
  status: string;
  activated_at?: string;
  created_at: string;
}

// ===== Restaurant =====
export interface Restaurant {
  name: string;
  address: string;
  phone?: string;
  rating?: string;
  category?: string;
  tags?: string[];
  longitude?: number;
  latitude?: number;
  distance?: string;
  opening_hours?: string;
  image_urls?: string[];
  reason?: string;
  recommended_dishes?: string[];
}

export interface RestaurantRecommendation {
  response: string;
  restaurants: Restaurant[];
  city?: string;
  recommendation_id?: number;
}

export interface SavedRestaurantRecommendation {
  id: number;
  session_id?: string;
  city: string;
  query: string;
  response: string;
  restaurants: Restaurant[];
  selected_restaurant?: Restaurant;
  created_at: string;
  updated_at: string;
}

// ===== Commerce =====
export interface Category {
  id: number;
  name: string;
  parent_id?: number;
  description: string;
  icon: string;
  sort_order: number;
  children: Category[];
}

export interface ProductListItem {
  id: number;
  name: string;
  price: number;
  original_price?: number;
  image_urls: string[];
  stock: number;
  unit: string;
  rating: number;
  status: string;
  source?: string;
}

export interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  original_price?: number;
  category_id?: number;
  image_urls: string[];
  stock: number;
  unit: string;
  specs: Array<{ name: string; options: string[] }>;
  tags: string[];
  rating: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CartItem {
  id: number;
  product_id: number;
  product_name: string;
  product_image: string;
  price: number;
  unit: string;
  quantity: number;
  specs: Record<string, string>;
  created_at: string;
}

export interface Cart {
  id: number;
  items: CartItem[];
  total_amount: number;
  created_at: string;
  updated_at: string;
}

export interface OrderItem {
  product_id: number;
  name: string;
  price: number;
  quantity: number;
  specs: Record<string, string>;
  image_url: string;
}

export interface Order {
  id: number;
  status: string;
  total_amount: number;
  items: OrderItem[];
  shipping_address: string;
  contact_phone: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface OrderListItem {
  id: number;
  status: string;
  total_amount: number;
  item_count: number;
  first_item_name: string;
  created_at: string;
}

// ===== Feedback =====
export interface RecommendationFeedback {
  content_type: string;
  message_id: string;
  feedback: "like" | "dislike";
  content_snapshot?: Record<string, unknown>;
  context?: Record<string, unknown>;
}
