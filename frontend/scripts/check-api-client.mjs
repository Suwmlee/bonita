/**
 * 禁止在业务代码里手写 /api/v1 请求；应使用 generate-client 产出的 *Service。
 * 允许：拼 resource 图片 URL、鉴权挂载、生成目录本身。
 */
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "src")
const skipDirs = new Set([path.join(root, "client")])

const rawCallWithApiRe = /\bclient\.(get|post|put|patch|delete)\s*(?:<[^>]*>)?\s*\(\s*\{[\s\S]*?url:\s*['"`]\/api\/v1\//

const violations = []

function walk(dir) {
  for (const name of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, name.name)
    if (name.isDirectory()) {
      if (skipDirs.has(full)) continue
      walk(full)
      continue
    }
    if (!/\.(ts|vue)$/.test(name.name)) continue
    const text = fs.readFileSync(full, "utf8")
    let match
    const re = new RegExp(rawCallWithApiRe.source, "g")
    while ((match = re.exec(text)) !== null) {
      const line = text.slice(0, match.index).split(/\r?\n/).length
      const snippet = match[0].replace(/\s+/g, " ").slice(0, 120)
      violations.push(`${path.relative(root, full)}:${line}: ${snippet}`)
    }

    // stores 里禁止出现业务 /api/v1 字符串（图片 baseURL 拼装应放 utils/composables）
    if (full.includes(`${path.sep}stores${path.sep}`) && /['"`]\/api\/v1\//.test(text)) {
      text.split(/\r?\n/).forEach((lineText, i) => {
        if (/['"`]\/api\/v1\//.test(lineText)) {
          violations.push(
            `${path.relative(root, full)}:${i + 1}: ${lineText.trim()}`,
          )
        }
      })
    }
  }
}

walk(root)

if (violations.length) {
  console.error("Found hand-written /api/v1 calls. Use generate-client *Service instead:\n")
  for (const v of [...new Set(violations)]) console.error(`  ${v}`)
  console.error("\nRun: pnpm run generate-client")
  process.exit(1)
}

console.log("OK: no hand-written /api/v1 business calls in stores (and no raw client+/api/v1 elsewhere)")
