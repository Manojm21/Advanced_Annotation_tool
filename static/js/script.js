var canvas = new fabric.Canvas('canvas', { width: 700, height: 500 });
    var currentClass = '';
    var drawingMode = false;
    var zoomEnabled = false;
    var zoomFactor = 1; // Track current zoom level

    canvas.on('mouse:wheel', updateObjectCoordinates);
    canvas.on('mouse:move', updateObjectCoordinates);
    canvas.on('mouse:up', updateObjectCoordinates);
    function enableResizing(rect) {
      console.log("check check ")
      rect.setControlsVisibility({
        mt: true,
        mb: true,
        ml: true,
        mr: true,
        tl: true,
        tr: true,
        br: true,
        bl: true,
        mtr: false
      });
      // Make the object selectable again for resizing
      rect.selectable = true;
    
      canvas.renderAll();
    }


    function resetAddClass() {
    // Remove all options from the dropdown menu except the default one
    var classDropdown = document.getElementById('class-dropdown');
    classDropdown.options.length = 10; // Assuming the first option is the default one

    // Clear the classes stored in localStorage
    localStorage.removeItem('classes');
}



function updateObjectCoordinates() {
  canvas.getObjects().forEach(function(object) {
    if (object.type === 'rect') {
      object.set({
        left: object.left * zoomFactor,
        top: object.top * zoomFactor,
        width: object.width * zoomFactor,
        height: object.height * zoomFactor
      });
    }
  });
  canvas.renderAll();
}

canvas.on('zoom', updateObjectCoordinates);
canvas.on('panning', updateObjectCoordinates);


    function loadCanvas() {
      var filename = "{{filename}}"; // Replace "4.png" with the actual filename
      var img = new Image();
      img.onload = function() {
        var scale = Math.min(canvas.width / img.width, canvas.height / img.height);
        var imgInstance = new fabric.Image(img, {
          scaleX: scale,
          scaleY: scale,
          selectable: false // Make the image unselectable
        });
        canvas.add(imgInstance);
      };
      img.src = 'uploads/' + filename;
    }
    loadCanvas();

    var annotations = [];

    function saveAnnotation() {
  var data = {
    filename: "{{filename}}" + ".txt", // Replace "4.png" with the actual filename
    annotations: annotations.map(function(annotation) {
      return {
        x: annotation.annotation.x / zoomFactor, // Adjust X coordinate based on zoom
        y: annotation.annotation.y / zoomFactor, // Adjust Y coordinate based on zoom
        class: annotation.annotation.class,  // Add class property
        width: annotation.annotation.width,
        height: annotation.annotation.height,
        // ... other annotation properties (if needed)
      };
    })
  };

  fetch('/save_annotation', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify(data)
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      alert('Annotation saved successfully!');
    } else {
      alert('Failed to save annotation!');
    }
  })
  .catch(error => {
    console.error('Error:', error);
  });
}


function addClass() {
    var newClass = document.getElementById('new-class').value.trim();
    if (newClass !== '') {
        var classDropdown = document.getElementById('class-dropdown');
        var option = document.createElement('option');
        
        // Assigning value starting from 11
        option.value = classDropdown.options.length + 10;
        
        option.text = newClass;
        classDropdown.appendChild(option);

        // Store the added class in localStorage
        var classes = JSON.parse(localStorage.getItem('classes')) || [];
        classes.push(newClass);
        localStorage.setItem('classes', JSON.stringify(classes));
    }
}



    function toggleDrawingMode() {
      drawingMode = !drawingMode;
      if (drawingMode) {
        canvas.selection = false;
        canvas.defaultCursor = 'crosshair';
        canvas.on('mouse:down', onMouseDown);
        disableZoom();
      } else {
        canvas.selection = true;
        canvas.defaultCursor = 'default';
        canvas.off('mouse:down', onMouseDown);
      }
      document.getElementById('draw-bounding-box-button').classList.toggle('button-used');
    }

    function onMouseDown(options) {
      
      if (drawingMode && options.target && options.target.type === 'image') {
        var startPoint = canvas.getPointer(options.e);
        var rect = new fabric.Rect({
          left: startPoint.x,
          top: startPoint.y,
          width: 0,
          height: 0,
          stroke: 'rgba(41, 207, 244,0.6)',
          strokeWidth: 2,
          fill: 'rgba(41, 207, 244,0.4)', // Transparent fill
          selectable: true,
          originX: 'left',
          originY: 'top'
        });
        canvas.on('mouse:move', onMouseMove);
        canvas.on('mouse:up', onMouseUp);
        canvas.add(rect);
        enableResizing(rect);
        var isLockedX = rect.get('lockScalingX');
        var isLockedY = rect.get('lockScalingY');

        console.log("Lock scaling X:", isLockedX);
        console.log("Lock scaling Y:", isLockedY);
      }
    }

    function onMouseMove(options) {
    if (drawingMode) {
         console.log("check1112");
        var endPoint = canvas.getPointer(options.e);
        var rect = canvas.item(canvas.getObjects().length - 1);
        
        // Calculate width and height based on mouse position
        var width = endPoint.x - rect.left;
        var height = endPoint.y - rect.top;
        
        // Ensure width and height are non-negative
        width = Math.max(width, 0);
        height = Math.max(height, 0);
        
        // Update rectangle properties
        rect.set({
            width: width,
            height: height
        });
        
        canvas.renderAll();
    }
}


   
function onMouseUp(options) {
    if (drawingMode) {
        canvas.off('mouse:move', onMouseMove);
        canvas.off('mouse:up', onMouseUp);
        canvas.renderAll(); 
        var rect = canvas.item(canvas.getObjects().length - 1);
        console.log("hello")
        var annotationObject = {
            annotation: {
                class: document.getElementById('class-dropdown').value,
                x: rect.left,
                y: rect.top,
                width: rect.width,
                height: rect.height
            },
            object: rect 
        };

        annotations.push(annotationObject);
        // document.getElementById('save-annotation-button').classList.add('button-used');
    }
}


function toggleZoom() {
    zoomEnabled = !zoomEnabled;
    if (zoomEnabled) {
        enableZoom();
    } else {
        disableZoom();
    }
    document.getElementById('zoom-toggle').classList.toggle('button-used');
}

function enableZoom() {
    var scale = 1,
        lastPosX = 0,
        lastPosY = 0,
        isPanning = false;

    canvas.wrapperEl.style.cursor = 'grab';

    canvas.wrapperEl.addEventListener('mousedown', function (e) {
        if (canvas.isDrawingMode || !zoomEnabled) {
            return;
        }
        isPanning = true;
        lastPosX = e.clientX;
        lastPosY = e.clientY;
        canvas.wrapperEl.style.cursor = 'grabbing';
    });

    canvas.wrapperEl.addEventListener('mousemove', function (e) {
        if (!isPanning || !zoomEnabled) {
            return;
        }
        const deltaX = e.clientX - lastPosX;
        const deltaY = e.clientY - lastPosY;

        canvas.relativePan(new fabric.Point(deltaX, deltaY));
        lastPosX = e.clientX;
        lastPosY = e.clientY;
    });

    canvas.wrapperEl.addEventListener('mouseup', function () {
        if (!zoomEnabled) {
            return;
        }
        isPanning = false;
        canvas.wrapperEl.style.cursor = 'grab';
    });

    canvas.wrapperEl.addEventListener('mouseleave', function () {
        if (!zoomEnabled) {
            return;
        }
        isPanning = false;
        canvas.wrapperEl.style.cursor = 'grab';
    });

    canvas.wrapperEl.addEventListener('wheel', function (e) {
        if (!zoomEnabled) {
            return;
        }
        var pointer = canvas.getPointer(e);
        var zoom = canvas.getZoom();
        var zoomFactor = 1.05; // Adjust the zoom factor for slower zoom speed
        var newZoom = zoom;

        if (e.deltaY > 0) {
            newZoom = zoom / zoomFactor;
        } else {
            newZoom = zoom * zoomFactor;
        }

        // Limit zoom level between 0.5 and 5
        newZoom = Math.max(0.5, Math.min(5, newZoom));

        // Check if zoom out goes below the original size
        if (newZoom < 1) {
            newZoom = 1;
        }

        var zoomX = pointer.x;
        var zoomY = pointer.y;

        canvas.zoomToPoint({ x: zoomX, y: zoomY }, newZoom);

        e.preventDefault();
        e.stopPropagation();
        canvas.defaultCursor = 'zoom-in';
    });
}

function disableZoom() {
    canvas.off('mouse:wheel');
    canvas.defaultCursor = 'default';
}

var deleteMode = false; // Track delete annotation mode
var isDrawingBox = false; // Track if drawing bounding box

function deleteAnnotationsInBox() {
    deleteMode = !deleteMode; // Toggle delete mode

    if (deleteMode) {
        // Add event listeners for mouse events on canvas
        canvas.on('mouse:down', onMouseDownDelete);
        canvas.on('mouse:move', onMouseMoveDelete);
        canvas.on('mouse:up', onMouseUpDelete);
        document.getElementById('delete-annotation-button').classList.add('button-used');
    } else {
        // Remove event listeners for mouse events on canvas
        canvas.off('mouse:down', onMouseDownDelete);
        canvas.off('mouse:move', onMouseMoveDelete);
        canvas.off('mouse:up', onMouseUpDelete);
        document.getElementById('delete-annotation-button').classList.remove('button-used');
        isDrawingBox = true; // Reset drawing box flag when delete mode is turned off
    }
}

function onMouseDownDelete(options) {
    if (!drawingMode && !isDrawingBox) {
        isDrawingBox = true;
        startPoint = canvas.getPointer(options.e); // Capture initial click coordinates
    
        boundingBox = new fabric.Rect({
            left: startPoint.x,
            top: startPoint.y,
            width: 0,
            height: 0,
            fill: 'rgba(0,0,0,0)', // Transparent fill
            stroke: 'black',
            strokeWidth: 0.5,
            selectable: true
        });
        canvas.add(boundingBox);
    }
}

function onMouseMoveDelete(options) {
    if (isDrawingBox) {
        var pointer = canvas.getPointer(options.e);
        var box = new fabric.Rect({
            left: Math.min(startPoint.x, pointer.x),
            top: Math.min(startPoint.y, pointer.y),
            width: Math.abs(pointer.x - startPoint.x),
            height: Math.abs(pointer.y - startPoint.y),
            fill: 'rgba(0,0,0,0)',
            stroke: 'black',
            strokeWidth: 0.5,
            selectable: true
        });
        canvas.remove(boundingBox); // Remove previous box (if any)
        canvas.add(box);
        boundingBox = box;
        canvas.renderAll();
    }
}

function onMouseUpDelete(options) {
    if (isDrawingBox) {
        isDrawingBox = false;
        document.getElementById('delete-annotation-button').classList.add('button-used');
        var endPoint = canvas.getPointer(options.e);
        var boxCoords = boundingBox.getBoundingRect();

        // Array to store annotations to delete
        var annotationsToDelete = [];

        // Iterate over all objects on the canvas
        canvas.getObjects().forEach(function(object) {
            // Check if the object is a rectangle (annotation)
            if (object.type === 'rect') {
                var rect = object.getBoundingRect();
                console.log("yes correct")
                console.log(rect);
                // Check for intersection between the annotation and the bounding box
                if (
                    rect.left <= boxCoords.left + boxCoords.width &&
                    rect.left + rect.width >= boxCoords.left &&
                    rect.top <= boxCoords.top + boxCoords.height &&
                    rect.top + rect.height >= boxCoords.top
                ){
                    annotationsToDelete.push(object);
                    console.log("yes correct1")
                }
            }
        });
        console.log(annotations)
        console.log(annotationsToDelete)
        // Remove annotations from the canvas
        annotationsToDelete.forEach(function(object) {
          console.log(object);
          console.log("deleted")
            canvas.remove(object);
            console.log("Object removed");
        });

        // Remove the bounding box
        canvas.remove(boundingBox);

        // Clear the annotations array
        console.log("check1",annotations.length)
        console.log("check1",annotationsToDelete.length)
        annotations = annotations.filter(function(annotation) {
            return !annotationsToDelete.includes(annotation.object);
        });
        console.log("check2",annotations.length)

    }
}
window.addEventListener('load', function() {
        var storedClasses = JSON.parse(localStorage.getItem('classes')) || [];
        var classDropdown = document.getElementById('class-dropdown');
        storedClasses.forEach(function(className, index) {
            var option = document.createElement('option');
            option.value = index;
            option.text = className;
            classDropdown.appendChild(option);
        });
    });



    // // #------------------------------------------------------\
    // canvas.on('mouse:down', function(event) {
    //     // Get the clicked point coordinates
    //     var pointer = canvas.getPointer(event.e);
    //     var x = pointer.x;
    //     var y = pointer.y;

    //     // Iterate over all objects on the canvas
    //     canvas.getObjects().forEach(function(object) {
    //         // Check if the clicked point is inside the bounding box
    //         if (object.type === 'rect' && x >= object.left && x <= object.left + object.width && y >= object.top && y <= object.top + object.height) {
    //             // If the clicked point is inside the bounding box, select it
    //             canvas.setActiveObject(object);
    //             canvas.renderAll();

    //             // Perform template matching on the selected bounding box
    //             performTemplateMatching();
    //         }
    //     });
    // });

    // async function performTemplateMatching() {
    //     var selectedObject = canvas.getActiveObject();
    //     if (selectedObject && selectedObject.type === 'rect') {
    //         var boundingBox = {
    //             x: selectedObject.left,
    //             y: selectedObject.top,
    //             width: selectedObject.width,
    //             height: selectedObject.height,
    //             class: selectedObject.class // Extracting class from selected object
    //         };
    //         var matchedRegions = await templateMatching("path/to/input/image.jpg", "path/to/templates/folder", boundingBox);
    //         highlightBoundingBoxes(matchedRegions);
    //         saveAnnotationWithHighlight(matchedRegions);
    //     } else {
    //         alert("Please select a bounding box to perform template matching.");
    //     }
    // }

    // async function templateMatching(inputImage, templatesFolder, boundingBox) {
    //     // Convert the bounding box to the required format for template matching
    //     var boundingBoxData = {
    //         x1: boundingBox.x,
    //         y1: boundingBox.y,
    //         x2: boundingBox.x + boundingBox.width,
    //         y2: boundingBox.y + boundingBox.height,
    //         class: boundingBox.class
    //     };

    //     // Make a POST request to the server for template matching
    //     var response = await fetch('/perform_template_matching', {
    //         method: 'POST',
    //         headers: {
    //             'Content-Type': 'application/json'
    //         },
    //         body: JSON.stringify({
    //             inputImage: inputImage,
    //             templatesFolder: templatesFolder,
    //             boundingBox: boundingBoxData
    //         })
    //     });

    //     // Parse the response
    //     var matchedRegions = await response.json();
    //     return matchedRegions;
    // }

    // function highlightBoundingBoxes(matchedRegions) {
    //     // Iterate over matched regions and highlight them on the canvas
    //     matchedRegions.forEach(region => {
    //         var rect = new fabric.Rect({
    //             left: region.x,
    //             top: region.y,
    //             width: region.width,
    //             height: region.height,
    //             stroke: 'green',
    //             strokeWidth: 2,
    //             fill: 'rgba(0,0,0,0)',
    //             selectable: false
    //         });
    //         canvas.add(rect);
    //         canvas.renderAll();
    //     });
    // }

    // async function saveAnnotationWithHighlight(matchedRegions) {
    //     // Your existing code to save annotations with highlighted regions remains unchanged
    // }
  