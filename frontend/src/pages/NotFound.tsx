import { Link, useLocation } from "react-router-dom";
import { useEffect } from "react";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error("404: route not found:", location.pathname);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-6">
      <div className="max-w-md text-center">
        <p className="font-mono text-sm uppercase tracking-[0.16em] text-muted-foreground">Page not found</p>
        <h1 className="mt-3 font-display text-3xl font-semibold tracking-tight text-foreground">
          We couldn't find that page
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          The link may be out of date, or the page may have moved. Your data and reports are safe.
        </p>
        <Link
          to="/"
          className="focus-calm mt-7 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-accent"
        >
          Back to Overview
        </Link>
      </div>
    </div>
  );
};

export default NotFound;
