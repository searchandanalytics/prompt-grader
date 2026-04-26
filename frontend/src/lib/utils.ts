import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function scoreColor(score: number): string {
  if (score >= 80) return 'text-green-600'
  if (score >= 60) return 'text-yellow-600'
  return 'text-red-500'
}

export function scoreBg(score: number): string {
  if (score >= 80) return 'bg-green-100 border-green-300'
  if (score >= 60) return 'bg-yellow-100 border-yellow-300'
  return 'bg-red-100 border-red-300'
}

export function scoreBar(score: number): string {
  if (score >= 80) return 'bg-green-500'
  if (score >= 60) return 'bg-yellow-500'
  return 'bg-red-500'
}
