# Remote publication contract

**唯一对外稳定更新源：**

```text
https://architectureworld.github.io/blender-designerBIM/index.json
```

使用 GitHub Pages 发布 Blender v1 静态扩展仓库。页面内只发布当前版本的 `index.json`、同域名 ZIP 与 `.nojekyll`。发布前后验证 ZIP 字节数、SHA-256、ZIP 根目录和扩展 manifest。一条 `.github/workflows/publish.yml` 负责全部发布，不保留仓库内的旧版静态索引副本和第二套工作流。

## 发布流程

1. 在开发支线完成修改和 `python -m pytest -q`。
2. 增加 `blender_manifest.toml` 的版本号。已经发布的版本和包不能覆盖。
3. 新增相应的 `docs/releases/vX.Y.Z.md`，记录测试内容及 Blender 运行验收边界。
4. 合并到 `main`，manifest 更新触发 `Publish Blender extension`。
5. GitHub Actions 测试和打包，然后创建不可覆盖的 GitHub Release。
6. 下载验证 Release ZIP；生成 Pages 站点并部署，最后通过公开 Pages URL 检查真实下载（含 Blender 平台/版本查询参数）。
7. 在 Actions 中复核成功状态；不能把 Python 及分发检查当作 Blender 5.2.2 实机验收。

首次部署需由仓库管理员在 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。未启用前不能宣称新 URL 可用。

## 开发/验证

```bash
python -m pytest -q
python scripts/build_release.py --out dist
python -m scripts.build_pages_site --index dist/index.json --package dist/designer_bim_p01-0.3.1-blender5.2.2.zip --output site
python scripts/verify_remote.py --expected-version 0.3.1
```

`build_release.py` 的中间版本索引仅用于核对 GitHub Release 的不可变归档；用户安装更新只使用 Pages。源代码中的实际 runtime 测试见 Blender 5.2.2 相关脚本与 Actions，不会因分发通过而被视为实机通过。

## Primary specifications

- https://docs.blender.org/manual/en/latest/advanced/extensions/creating_repository/static_repository.html
- https://developer.blender.org/docs/features/extensions/api_listing/v1/
- https://docs.blender.org/manual/en/latest/editors/preferences/extensions.html
- https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
