[![thumbnail_new2025](https://github.com/user-attachments/assets/bd212809-7dd3-4208-997c-2d30a9efa44e)](https://www.youtube.com/watch?v=wc7xVZXAwYQ)  
Click for the video!  
# ✨ OptiPloy: The Appending/Linking Upgrade
TL;DR: You WILL save GIGABYTES in storage. Less duplication!

OptiPloy introduces a balance between appending and linking, something that has not yet existed as a one-click solution. This is limited to objects and collections.

## 🚀 Key Features

- **Hybrid Importing**  
  Choose from 15 data types to localize or to leave linked to the source file. Object and Collection types are enabled by default.
- **Fine‑Grained Control**  
  Save importing preferences globally, per-folder, or per-blend.
- **One‑Click Workflow**  
  Spawn assets directly from the side‑panel without manual linking/appending.  
- **No Duplicating Boneshapes**  
  Boneshapes do *not* duplicate, not even if you choose to localize armatures.
- **Auto-Execute Scripts & Scriptable Hook**  
  OptiPloy will automatically execute data blocks associated with your import. This ensures, for example, that Rigify UI scripts work right off the bat. 
  
  For your own scripts, access newly spawned objects via `bpy.context.scene['new_spawn']`
- **And so much more! Really! Scroll down for the full list!**

## ❔ Why not just append or link?
Refer to the handy table:
| Method      | Pros                         | Cons                                 |
| ----------- | ---------------------------- | ------------------------------------ |
| Appending   | Instant copy, fully editable | Duplicates file size with each paste |
|             | Very easy                    | Easy to start bad habits for new users |
| Linking     | Minimal storage, just recycling | Requires overrides to even slightly edit   |
|             | Able to update data from source file | Can be tedious to do right |
| **OptiPloy**| ✔️ Best of both              | —                                    |

## 📥 Quick Start

1. **Install**  
   - Blender 4.1-: *Edit → Preferences → Add-ons → Install → Select* `optiploy.zip`

   - Blender 4.2+: *Edit → Preferences → Get Extensions → Search* "OptiPloy"  
   or
   - *Edit → Preferences → Add-ons → Top-right dropdown menu → Install from disk... → Select* `optiploy.zip`

2. **Prepare .blend, Mark Assets**
   - Prepare any `.blend` files you plan to use by marking its Objects or Collections as assets

3. **Configure Add-on**  
   - *Edit → Preferences → Add-ons → OptiPloy*.  
   - Add `.blend` files individually or by the folder.  
    (Tip: Shift‑click **+** to create a category folder.)
   - Files will be automatically scanned for assets to spawn.

4. **Spawn Assets**  
   - *3D Viewport → Side-panel → OptiPloy*  
   - Search through `.blend` files to spawn assets!

## ⚙️ Detailed Usage

### Preferences Panel  
- **Mounted .blend Files**: Manage your search folders and .blend files, and see what assets are added.  
- **Update Catalogs**: Update your .blend files by using the `Scan` operator.

### Side-Panel
- Switch between the `.blend`, `Folder`, and `Tools` view mode
  - You can set the import options globally in the `Tools` view, or you can set them per-folder or per-blend through the <img src="https://raw.githubusercontent.com/Shrinks99/blender-icons/refs/heads/main/blender-icons/settings.svg" height=23> gear icons.
- Browse through the list of assets and spawn them.
- **RED-highlighted `.blend` Multi-tool**: An operator with the <img src="https://raw.githubusercontent.com/Shrinks99/blender-icons/refs/heads/main/blender-icons/blender.svg" height=23> icon exists to reload, open, or re-scan the active .blend file.
  - Hold `CTRL` to reload the .blend file as a library
  - Hold `SHIFT` to open the .blend file in a new instance of Blender
  - Hold `ALT`to re-scan the .blend file in OptiPloy

### Localization Options  
In the `Tools` view mode, you may choose to localize any of the following data types:
```
bpy.types.Collection
bpy.types.Object
bpy.types.Mesh
bpy.types.Material
bpy.types.SurfaceCurve
bpy.types.Light
bpy.types.Curve
bpy.types.GreasePencil
bpy.types.MetaBall
bpy.types.TextCurve
bpy.types.Volume
bpy.types.Armature
bpy.types.Camera
```
Setting these options affects imports as a whole, but localization options can also be set per-blend or per-folder.

### Asset Browser Integration
OptiPloy has an operator built-in to optimize Collections or Objects linked through the Asset Browser.
- Viewport / Operator Search Menu  
  Search for `Optimize with OptiPloy` and execute the operator
- Outliner
  Select the IDs you wish to localize (collections/objects), right click, and select `Optimize with OptiPloy`  

Again, for this to work, the assets need to be *linked* through the asset browser, not appended.

## 🖥️ For Developers
### Scripting Hook
OptiPloy automatically executes any text block associated with an import. You can access the data of the imported object through `bpy.context.scene['new_spawn']` to perform further adjustments or optimizations.
### Using Key Modifiers
Incorporate key modifiers (`CTRL`, `SHIFT`, `ALT`) into your scripts by accessing
```
bpy.context.scene['key_ctrl']
bpy.context.scene['key_shift']
bpy.context.scene['key_alt']
```
## Full Features
- **Hybrid Importing**  
  Choose from 15 data types to localize or to leave linked to the source file. Object and Collection types are enabled by default.
- **Fine‑Grained Control**  
  Save importing preferences globally, per-folder, or per-blend.
- **One‑Click Workflow**  
  Spawn assets directly from the side‑panel without manual linking/appending.  
- **No Duplicating Boneshapes**  
  Boneshapes do *not* duplicate, not even if you choose to localize armatures.
- **Auto-Execute Scripts & Scriptable Hook**  
  OptiPloy will automatically execute data blocks associated with your import. This ensures, for example, that Rigify UI scripts work right off the bat. 
- **.blend File Multi-tool**  
  Use CTRL, SHIFT, or ALT on the red Blender icon to reload, open, or re-scan the selected .blend file
- **Full Driver Functionality**  
  Despite all the localizing that takes place, drivers never lose their targets as they shift from linked to localized.
- **Hierarchal Localizing**  
  OptiPloy recursively builds a hierarchy of levels that IDs are referenced at, and localizes going down this hierarchy. This ensures no breakage when localizing.
- **Automatic Library Overrides**  
  Unlocalized IDs are given automatic library overrides to make some wiggle room for what can be edited.  
  To edit custom properties, make sure `Library Overridable` is enabled in its options.
- **Fun for Coders**  
  During the script execution stage at the end of the importing process, you can access the new import through `bpy.context.scene['new_spawn']`, letting you do further adjustments after it has been deployed.  
  Scripters can incorporate `CTRL`, `SHIFT`, and `ALT` into their scripts by using:
  ```
  bpy.context.scene['key_ctrl']
  bpy.context.scene['key_shift']
  bpy.context.scene['key_alt']
  ```  
  Attach text blocks to an import by assigning them as a custom property to any ID associated with the import.
- **Asset Library Integration**  
  An operator named `Optimize with OptiPloy` exists to optimize assets linked through the asset browser.  
  Viewport: Object → Optimize with OptiPloy  
  Outliner: Right-click → Optimize with OptiPloy  
## Donate
If you find that this addon has saved you time and storage, you may consider supporting my work.

[Ko-Fi Link](https://ko-fi.com/hisanimations)  
[Buy the version with thumbnail previews](hisanimations.gumroad.com/l/optiploy_thumbnails)