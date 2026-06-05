"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

export function TopLoader() {
  const pathname = usePathname();
  const [width, setWidth] = useState(0);
  const [show, setShow] = useState(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];

    setShow(true);
    setWidth(15);
    timers.current.push(setTimeout(() => setWidth(60), 120));
    timers.current.push(setTimeout(() => setWidth(88), 400));
    timers.current.push(
      setTimeout(() => {
        setWidth(100);
        timers.current.push(
          setTimeout(() => {
            setShow(false);
            setWidth(0);
          }, 250)
        );
      }, 750)
    );

    return () => {
      timers.current.forEach(clearTimeout);
    };
  }, [pathname]);

  return (
    <div
      aria-hidden="true"
      className="fixed top-0 left-0 z-[9999] h-0.5 bg-green-600 pointer-events-none"
      style={{
        width: `${width}%`,
        opacity: show ? 1 : 0,
        transition: "width 300ms ease-out, opacity 250ms ease",
      }}
    />
  );
}
