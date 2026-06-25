const config = {
	printWidth: 100,
	proseWrap: "preserve",
	tabWidth: 2,
	useTabs: false,
	overrides: [
		{
			files: "*.html",
			options: {
				parser: "html",
			},
		},
	],
};

export default config;
