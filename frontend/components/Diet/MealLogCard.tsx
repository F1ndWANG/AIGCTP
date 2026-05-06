"use client";

interface MealLogCardProps {
  record: {
    id?: number;
    meal_type: string;
    foods: Array<{ name: string; amount: string; calories?: number }>;
    total_nutrition?: { calories?: number; protein?: number; carbs?: number; fat?: number };
    notes?: string;
  };
  onDelete?: (id: number) => void;
}

const MEAL_LABELS: Record<string, string> = {
  breakfast: "早餐",
  lunch: "午餐",
  dinner: "晚餐",
  snack: "加餐",
};

const MEAL_COLORS: Record<string, string> = {
  breakfast: "bg-amber-100 text-amber-700",
  lunch: "bg-green-100 text-green-700",
  dinner: "bg-indigo-100 text-indigo-700",
  snack: "bg-pink-100 text-pink-700",
};

export default function MealLogCard({ record, onDelete }: MealLogCardProps) {
  const label = MEAL_LABELS[record.meal_type] || record.meal_type;
  const color = MEAL_COLORS[record.meal_type] || "bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300";
  const nutrition = record.total_nutrition;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border dark:border-slate-700 p-4">
      <div className="flex items-center justify-between mb-3">
        <span className={`text-xs font-bold px-2 py-0.5 rounded ${color}`}>
          {label}
        </span>
        {record.id && onDelete && (
          <button
            onClick={() => onDelete(record.id!)}
            className="text-xs text-red-400 hover:text-red-600"
          >
            删除
          </button>
        )}
      </div>

      <div className="space-y-1">
        {record.foods.map((food, i) => (
          <div key={i} className="flex justify-between text-sm">
            <span className="text-gray-700 dark:text-gray-300">
              {food.name}
              <span className="text-gray-400 dark:text-gray-500 ml-1">{food.amount}</span>
            </span>
            {food.calories ? (
              <span className="text-gray-500 dark:text-gray-400">{food.calories} kcal</span>
            ) : null}
          </div>
        ))}
      </div>

      {nutrition && (
        <div className="mt-3 pt-3 border-t dark:border-slate-700 grid grid-cols-4 gap-2 text-center text-xs">
          <div>
            <p className="text-gray-900 dark:text-gray-100 font-medium">{nutrition.calories || 0}</p>
            <p className="text-gray-400 dark:text-gray-500">卡路里</p>
          </div>
          <div>
            <p className="text-gray-900 dark:text-gray-100 font-medium">{nutrition.protein || 0}g</p>
            <p className="text-gray-400 dark:text-gray-500">蛋白质</p>
          </div>
          <div>
            <p className="text-gray-900 dark:text-gray-100 font-medium">{nutrition.carbs || 0}g</p>
            <p className="text-gray-400 dark:text-gray-500">碳水</p>
          </div>
          <div>
            <p className="text-gray-900 dark:text-gray-100 font-medium">{nutrition.fat || 0}g</p>
            <p className="text-gray-400 dark:text-gray-500">脂肪</p>
          </div>
        </div>
      )}

      {record.notes && (
        <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">{record.notes}</p>
      )}
    </div>
  );
}
