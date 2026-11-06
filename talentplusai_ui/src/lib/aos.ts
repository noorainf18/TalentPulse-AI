/** Landing-style stagger: pairs with `.aos-fade-up` + `.visible` (see globals.css). */
const AOS_DELAYS = ["aos-delay-1", "aos-delay-2", "aos-delay-3", "aos-delay-4", "aos-delay-5"] as const;

export function aosFadeStagger(step: number): string {
  return `aos-fade-up ${AOS_DELAYS[((step % 5) + 5) % 5]}`;
}
