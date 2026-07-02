import { EffectivenessDashboard } from "@/components/effectiveness-dashboard";

export default function EffectivenessPage() {
	return (
		<EffectivenessDashboard
			current={{ averageMastery: 0.74, learnerCount: 25, learnersDat: 17 }}
			previous={{ averageMastery: 0.68, learnerCount: 25, learnersDat: 16 }}
		/>
	);
}
