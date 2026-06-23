import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** shadcn standard cn() helper — merges Tailwind classes */
export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}
