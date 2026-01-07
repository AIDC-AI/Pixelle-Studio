/** @type {import('next').NextConfig} */
const nextConfig = {
    // Enable React strict mode for better development experience
    reactStrictMode: true,
    // Enable standalone output for Docker deployment
    output: "standalone",
}

export default nextConfig
