import Image from "next/image";
import { cn } from "@/lib/utils";

export function SkyreonLogo({
  variant = "full",
  className,
}: {
  variant?: "full" | "mark";
  className?: string;
}) {
  if (variant === "mark") {
    return (
      <Image
        src="/skyreon-mark.png"
        alt="Skyreon"
        width={102}
        height={102}
        className={cn("h-9 w-9 object-contain", className)}
        priority
      />
    );
  }

  return (
    <Image
      src="/skyreon-logo.png"
      alt="Skyreon"
      width={235}
      height={67}
      className={cn("h-9 w-auto object-contain object-left", className)}
      priority
    />
  );
}
