const path = require("node:path");

// Load YAML data imported by the working docs and release snapshots.
module.exports = function (context, options) {
  return {
    name: "yaml-data-loader",
    configureWebpack(config, isServer, utils) {
      return {
        module: {
          rules: [
            {
              test: /\.ya?ml$/,
              include: [
                path.resolve(__dirname, "..", "docs"),
                path.resolve(__dirname, "..", "versioned_docs"),
              ],
              use: path.resolve(__dirname, "js-yaml-loader.js"),
            },
          ],
        },
      };
    },
  };
};
