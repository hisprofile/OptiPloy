# Intro
Append and link rigs! Save space like never before! OptiPloy, the Optimized Deployment of rigs (and more) is now here.

OptiPloy (optimized deployment) can be considered a better alternative to appending and linking rigs, while having the best of both worlds. Appending them for full functionality, and linking all the data that composes the rig to reduce duplication. And that can save a LOT of space.

(Don't have a set of rigs to test it with? Try my TF2 Buildings port! https://drive.google.com/drive/folders/11vyl_97Xy8LE-VPECfLlJ876poRZp6AT?usp=drive_link)

# Here's how to set it up.
In the preferences, you will find two sections to add .blend files. Individually or by a folder of them. Now there are two things worth noting. OptiPloy will only spawn objects or collections, *if* they have been marked as assets. And two, sub-folders will NOT be parsed.

Once you have a .blend file prepared with a rig under a collection marked as an asset, you may now add that .blend file to OptiPloy. It will automatically be scanned for spawnable items, which you can spawn through the OptiPloy tab in the 3D Viewport.

# How does OptiPloy work?
Through the `bpy.data.libraries.load` feature, OptiPloy links an object/collection, applies library overrides over hierarchy, then localizes it as much as the user wishes. This is crucial for a fast-working spawning tool that compromises between the benefits of localized data and linked data. And since the localization options can be entry-specific, I have no doubt this could be a user-favorite when it comes to working with the tens to hundreds of rigs they frequently use.

## Linked vs. Library Overrides vs. Localized
When you link data from another file, you cannot edit that linked data because it is not yours. Everything about it comes from another file, therefore to make changes, you must edit in that source file.

Applying Library Overrides will let you edit *some* attributes on that data, but not everything. Library overrides is like putting data in a state between linked and localized.

Localizing data will make a fully local copy of that data. Depending on what is being localized, it *can* take up more storage, but you will have no limit on what you can edit.

It's nice to have local copies of what you know you'll want to edit, while having the rest of the data linked to the source file.

## Why would I want to localize data?
Localizing data allows you to edit the properties on that data to the fullest extent. For example, you are able to enter edit mode on a localized mesh, but not on a linked or overridden mesh. In OptiPloy, collections and objects are localized by default. But if a user knows they would like to edit the mesh of an object in the future, that user should have `Localize Meshes` enabled by default.

However, leaving things unlocalized gives users a chance to modify the data in the source file with the changes updating in any other file, so long as the changed attributes aren't overridden. This is great for mass modification in case a user errs.

Spawning the same data with different settings applied will not localize pre-existing data, so long as the data is that of collections, objects, materials, or any other object data type. (see [object data types](https://docs.blender.org/api/current/bpy_types_enum_items/object_type_items.html#rna-enum-object-type-items))

## To scripters
Optiploy assigns newly spawned items to a globally accessible variable, `context.scene['new_spawn']`. This gives you an opportunity to write a script to further modify data when OptiPloy executes any attached script. Say for example, you have a ragdoll rig and you need to initialize the Rigid Body World and assign collisions and constraints to collections used by the RBW.

# Last thing
In the tools view mode in the OptiPloy tab, you can choose whether to localize meshes, materials, images, node groups, and armature data by default. But if this data gets localized despite having these options disabled, that means they are localized because another asset requires them to be.

In the `Tools` view mode in the 3D viewport, you can choose which objects types should be localized or not. Any folder/blend entry can override these options by enabling so in their settings panel.

Here are the list of IDs that can be localized/overridden:

```
bpy.types.Collection,
bpy.types.Object,
bpy.types.Mesh,
bpy.types.Material,
bpy.types.SurfaceCurve,
bpy.types.Light,
bpy.types.Curve,
bpy.types.GreasePencil,
bpy.types.MetaBall,
bpy.types.TextCurve,
bpy.types.Volume,
bpy.types.Armature,
bpy.types.Camera
```

# FAQ
- **IDs like meshes and materials are duplicating when I spawn the same item more than once, despite having the localizing options off. What's going on?**
  - This is a good question. "Data Isolation" was a concept I struggled with when making OptiPloy. 
  
    Normally, when you spawn the same item again with more localizing options enabled, the data from the pre-existing item would get localized along with this new instance. To counteract this, a lot of supported IDs are given library overrides to put them in a state between linked and fully localized. While this does result in duplication, it doesn't use as much storage as it *could*. And it successfully isolates the data tied to the instance of that item, mostly preventing further modification from later spawns.

    Theoretically, this data isolation can be done without library overrides. In practice, I've achieved this by having another instance of Blender load, modify, and save the data for the main instance to use in real time. Despite how interesting this concept was, I doubt users would be happy with a background instance of Blender running for each main instance. Another way this could be achieved is by using the `bpy.types.BlendData.temp_data()` function to act as the "second instance", but it would cause Blender to crash whenever linking data in this temp_data context. If it didn't crash, it would always prompt the user with a "corrupt data" warning.

- **I get tons of "bke.liboverride" errors when spawning something!**
  - This happens when localizing collections, objects, or possibly more, if they were given library overrides over hierarchy. However, I feel that these errors are of empty meaning and that Blender sorts it out itself. All the data is fine when saving and reloading a file.

# Donate
If this rig saves you a bunch of space, and time, you just might consider supporting!
https://ko-fi.com/hisanimations

# Credits
Thank you to LetUmGo ( https://www.youtube.com/@Letumgo ) for helping with the logo!
