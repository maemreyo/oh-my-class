import type { Metadata } from "next";
import { QueryProvider } from "@/lib/query-client";
import { RootLayoutClient } from "./_components/root-layout-client";
import "./globals.css";

export const metadata: Metadata = {
	title: "oh-my-class — Teacher Dashboard",
	description: "AI-powered teaching pack generator for K-12 education",
};

export default function RootLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return (
		<html lang="vi">
			<body className="min-h-screen bg-background font-sans antialiased">
				<RootLayoutClient>
					<QueryProvider>{children}</QueryProvider>
				</RootLayoutClient>
			</body>
		</html>
	);
}
