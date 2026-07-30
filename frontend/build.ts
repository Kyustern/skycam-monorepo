import 'bun'

await Bun.build({
  entrypoints: ["./src/main.tsx"],
  outdir: "./out",

});