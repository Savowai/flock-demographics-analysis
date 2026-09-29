/** @type {import('next').NextConfig} */
const nextConfig = {
  // DuckDB-WASM and Transformers.js need these headers for SharedArrayBuffer
  // and cross-origin isolation when running multi-threaded builds.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
          { key: "Cross-Origin-Embedder-Policy", value: "credentialless" },
        ],
      },
    ];
  },
};
export default nextConfig;
