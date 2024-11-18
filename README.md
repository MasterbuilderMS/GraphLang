# GraphLang
Programming language written for desmos

# Installation
- To install, download the executable from the releases page
- write your graphlang code onto a file and save it with a `.graphlang` extension
- right click the graphlang file in file explorer, and click open with
- click browse my pc. Find the executable you downloaded and select it
- click always
- done! 
- the compiled desmos will be copied to clipboard!
- In order to enter this into desmos, install the desmos text i/o extension (thanks to hyrodium at https://github.com/hyrodium/desmos-text-io/ for this project!)
### Warning - many of these features could be unstable or will be changed at a later date!

# Current Features
 - expressions such as `y = x`
 - Namespaces - maps to desmos folders `ns Namespace{`
 - Functions `fn Function {`
 - Lists `[1,2,3,4]` (list comprehension soon)
 - Many desmos functions, e.g. sin, cos , tan
 - polygons
 - Pre-compilation variable checking
 - Namespace dot notation
 - Proper scoping sytem
 - Function calls
 - Macros
 - Imports from other graphlang files
 - Beginings of a stdlib

## v3.0
 - [ ] Waaaaay better error messages
 - [ ] Conditional statements
 - [ ] List comp
 - [ ] Bug fixes
## v4.0+
   - [ ] expression evaluation e.g. 1+1 ---> 2
   - [ ] Further desmos abstraction: make desmos more similar to other languages
   - [ ] standard library containing:
       - [ ] GUI tools
       - [ ] Shapes library
       - [ ] Physics
       - [ ] Game
       - [ ] Inputs - keyboard, buttons
       - [ ] Program creation and better actions ( `=` functions like `->` like in regular languages)
       - [ ] tone
       - [ ] piecewises
   - [ ] Python macro api
   - [ ] Optimisations (wakascopes, see https://radian628.github.io/unofficial-desmos-wiki/performance/desmos-performance-techniques/)
   - [ ] Possible auto update (no copy and paste needed)


