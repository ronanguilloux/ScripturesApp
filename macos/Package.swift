// swift-tools-version: 5.9
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "BibleApp",
    platforms: [
        .macOS(.v12)
    ],
    products: [
        .executable(name: "BibleApp", targets: ["BibleApp"]),
    ],
    targets: [
        .executableTarget(
            name: "BibleApp"),
    ]
)
