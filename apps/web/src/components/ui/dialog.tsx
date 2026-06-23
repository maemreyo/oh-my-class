"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as React from "react";
import { cn } from "@/lib/utils";

const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogClose = DialogPrimitive.Close;

const DialogContent = React.forwardRef<
	React.ComponentRef<typeof DialogPrimitive.Content>,
	React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...props }, ref) => (
	<DialogPrimitive.Portal>
		<DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/80" />
		<DialogPrimitive.Content
			ref={ref}
			className={cn(
				"fixed left-[50%] top-[50%] z-50 w-full max-w-lg translate-x-[-50%] translate-y-[-50%] rounded-lg border bg-background p-6 shadow-lg",
				className,
			)}
			{...props}
		>
			{children}
		</DialogPrimitive.Content>
	</DialogPrimitive.Portal>
));
DialogContent.displayName = DialogPrimitive.Content.displayName;

export { Dialog, DialogClose, DialogContent, DialogTrigger };
