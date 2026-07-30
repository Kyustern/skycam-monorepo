import type { Config } from "tailwindcss";

export default {
	content: [
		"./pages/**/*.{ts,tsx}",
		"./components/**/*.{ts,tsx}",
		"./app/**/*.{ts,tsx}",
		"./src/**/*.{ts,tsx}",
	],
	prefix: "",
	darkMode: 'class',
	theme: {
		extend: {
			colors: {
				// Light theme colors
				'sidebar': '#f8f9fa',
				'sidebar-foreground': '#212529',
				'sidebar-primary': '#6c757d',
				'sidebar-primary-foreground': '#ffffff',
				'sidebar-accent': '#e9ecef',
				'accent': '#6c757d',
			},
		},
	},
	plugins: [],
} satisfies Config;