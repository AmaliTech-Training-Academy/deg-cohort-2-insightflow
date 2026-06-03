"use client";

import { useState } from "react";
import Link from "next/link";
import { forgotPassword } from "@/api/auth";

type Step = "form" | "sent";

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<Step>("form");
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState("");
  const [loading, setLoading] = useState(false);
  const [serverError, setServerError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setEmailError("Enter a valid email address.");
      return;
    }
    setEmailError("");
    setServerError("");
    setLoading(true);
    try {
      await forgotPassword(email);
      setStep("sent");
    } catch {
      setServerError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center relative px-4">
      <button
        type="button"
        title="Toggle dark mode"
        className="absolute top-4 right-4 p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-200 transition-colors"
      >
        <MoonIcon />
      </button>

      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 px-8 py-8">
          {/* Logo */}
          <div className="flex flex-col items-center gap-2 mb-7">
            <InsightFlowIcon />
            <span className="text-lg font-semibold text-gray-900 tracking-tight">
              InsightFlow
            </span>
          </div>
          {step === "form" ? (
            <>
              <h1 className="text-2xl font-bold text-gray-900 mb-1">
                Reset your password
              </h1>
              <p className="text-sm text-gray-500 mb-6">
                Enter your email and we&apos;ll send you a reset link.
              </p>

              {serverError && (
                <div className="mb-5 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                  {serverError}
                </div>
              )}

              <form onSubmit={handleSubmit} noValidate className="space-y-4">
                <div>
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-gray-700 mb-1.5"
                  >
                    Email
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
                      <EnvelopeIcon />
                    </span>
                    <input
                      id="email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@insightflow.io"
                      className={`w-full pl-9 pr-4 py-2.5 border rounded-lg text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-shadow ${
                        emailError ? "border-red-400" : "border-gray-300"
                      }`}
                    />
                  </div>
                  {emailError && (
                    <p className="mt-1 text-xs text-red-600">{emailError}</p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {loading ? "Sending…" : "Send reset link"}
                </button>
              </form>

              <div className="mt-5 pt-5 border-t border-gray-100 text-center text-sm text-gray-500">
                Remember your password?{" "}
                <Link
                  href="/login"
                  className="text-green-600 hover:text-green-700 font-medium transition-colors"
                >
                  Back to sign in
                </Link>
              </div>
            </>
          ) : (
            /* Success state */
            <div className="text-center py-4">
              <div className="flex items-center justify-center w-14 h-14 bg-green-50 rounded-full mx-auto mb-5">
                <EnvelopeSentIcon />
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2">
                Check your inbox
              </h2>
              <p className="text-sm text-gray-500 mb-1">
                We sent a password reset link to
              </p>
              <p className="text-sm font-medium text-gray-800 mb-6">{email}</p>
              <p className="text-xs text-gray-400 mb-6">
                Didn&apos;t receive it? Check your spam folder or{" "}
                <button
                  type="button"
                  onClick={() => setStep("form")}
                  className="text-green-600 hover:text-green-700 font-medium transition-colors"
                >
                  try another address
                </button>
                .
              </p>
              <Link
                href="/login"
                className="inline-flex items-center gap-2 text-sm text-green-600 hover:text-green-700 font-medium transition-colors"
              >
                <ArrowLeftIcon />
                Back to sign in
              </Link>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

function InsightFlowIcon() {
  return (
    <div className="w-9 h-9 bg-green-600 rounded-xl flex items-center justify-center shrink-0">
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="white"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <polyline points="3,12 7,12 9,5 12,19 15,8 17,12 21,12" />
      </svg>
    </div>
  );
}

function MoonIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

function EnvelopeIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="2" y="4" width="20" height="16" rx="2" />
      <path d="M22 7L12 13 2 7" />
    </svg>
  );
}

function EnvelopeSentIcon() {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 24 24"
      fill="none"
      stroke="#16a34a"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="2" y="4" width="20" height="16" rx="2" />
      <path d="M22 7L12 13 2 7" />
      <path d="M8 14l-2 2 2 2" />
      <path d="M6 16h4" />
    </svg>
  );
}

function ArrowLeftIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M19 12H5" />
      <path d="M12 19l-7-7 7-7" />
    </svg>
  );
}
