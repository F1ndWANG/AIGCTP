"use client";

import { useState } from "react";
import type { HealthProfile } from "@/lib/types";

interface HealthProfileFormProps {
  profile?: HealthProfile | null;
  onSave: (data: Partial<HealthProfile>) => Promise<void>;
}

const DIET_GOAL_OPTIONS = [
  { value: "weight_loss", label: "减肥" },
  { value: "muscle_gain", label: "增肌" },
  { value: "healthy", label: "健康饮食" },
  { value: "maintain", label: "维持体重" },
];

const RESTRICTION_OPTIONS = [
  { value: "vegetarian", label: "素食" },
  { value: "vegan", label: "纯素" },
  { value: "no_spicy", label: "不吃辣" },
  { value: "low_carb", label: "低碳水" },
  { value: "low_fat", label: "低脂" },
  { value: "halal", label: "清真" },
];

export default function HealthProfileForm({ profile, onSave }: HealthProfileFormProps) {
  const [height, setHeight] = useState(profile?.height?.toString() || "");
  const [weight, setWeight] = useState(profile?.weight?.toString() || "");
  const [age, setAge] = useState(profile?.age?.toString() || "");
  const [gender, setGender] = useState(profile?.gender || "");
  const [allergies, setAllergies] = useState(profile?.allergies?.join(", ") || "");
  const [conditions, setConditions] = useState(profile?.chronic_conditions?.join(", ") || "");
  const [goals, setGoals] = useState<string[]>(profile?.diet_goals || []);
  const [restrictions, setRestrictions] = useState<string[]>(profile?.dietary_restrictions || []);
  const [saving, setSaving] = useState(false);

  const toggleGoal = (val: string) => {
    setGoals((prev) =>
      prev.includes(val) ? prev.filter((g) => g !== val) : [...prev, val]
    );
  };

  const toggleRestriction = (val: string) => {
    setRestrictions((prev) =>
      prev.includes(val) ? prev.filter((r) => r !== val) : [...prev, val]
    );
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave({
        height: height ? parseFloat(height) : undefined,
        weight: weight ? parseFloat(weight) : undefined,
        age: age ? parseInt(age) : undefined,
        gender: gender || undefined,
        allergies: allergies ? allergies.split(/[,，]/).map((s) => s.trim()).filter(Boolean) : [],
        chronic_conditions: conditions ? conditions.split(/[,，]/).map((s) => s.trim()).filter(Boolean) : [],
        diet_goals: goals,
        dietary_restrictions: restrictions,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5">
      {!profile && (
        <p className="text-sm text-blue-600 bg-blue-50 rounded-lg px-3 py-2">
          尚未设置健康档案，完善信息后可获得更精准的饮食建议
        </p>
      )}

      {/* Basic Info */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">身高 (cm)</label>
          <input
            type="number"
            value={height}
            onChange={(e) => setHeight(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            placeholder="170"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">体重 (kg)</label>
          <input
            type="number"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            placeholder="65"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">年龄</label>
          <input
            type="number"
            value={age}
            onChange={(e) => setAge(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            placeholder="28"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">性别</label>
          <select
            value={gender}
            onChange={(e) => setGender(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          >
            <option value="">请选择</option>
            <option value="male">男</option>
            <option value="female">女</option>
          </select>
        </div>
      </div>

      {/* Allergies & Conditions */}
      <div>
        <label className="block text-sm font-medium text-gray-600 mb-1">过敏源（逗号分隔）</label>
        <input
          type="text"
          value={allergies}
          onChange={(e) => setAllergies(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          placeholder="花生, 海鲜, 牛奶"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-600 mb-1">慢性病（逗号分隔）</label>
        <input
          type="text"
          value={conditions}
          onChange={(e) => setConditions(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          placeholder="高血压, 糖尿病"
        />
      </div>

      {/* Diet Goals */}
      <div>
        <label className="block text-sm font-medium text-gray-600 mb-2">饮食目标</label>
        <div className="flex flex-wrap gap-2">
          {DIET_GOAL_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => toggleGoal(opt.value)}
              className={`text-xs px-3 py-1.5 rounded-full border transition ${
                goals.includes(opt.value)
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-600 border-gray-200 hover:border-blue-300"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Dietary Restrictions */}
      <div>
        <label className="block text-sm font-medium text-gray-600 mb-2">饮食限制</label>
        <div className="flex flex-wrap gap-2">
          {RESTRICTION_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => toggleRestriction(opt.value)}
              className={`text-xs px-3 py-1.5 rounded-full border transition ${
                restrictions.includes(opt.value)
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-600 border-gray-200 hover:border-blue-300"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Save */}
      <button
        onClick={handleSave}
        disabled={saving}
        className="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50"
      >
        {saving ? "保存中..." : "保存健康档案"}
      </button>
    </div>
  );
}
