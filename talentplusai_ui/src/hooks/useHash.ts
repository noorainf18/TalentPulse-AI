"use client";

import { useEffect, useState } from "react";

function readHash() {
  if (typeof window === "undefined") return "";
  return (window.location.hash.replace(/^#/, "") || "profile").toLowerCase();
}

/**
 * Current URL fragment for candidate detail tabs (#profile, #evidence, …).
 */
export function useHash() {
  const [hash, setHash] = useState(readHash);

  useEffect(() => {
    setHash(readHash());
    const onHash = () => setHash(readHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return hash;
}
