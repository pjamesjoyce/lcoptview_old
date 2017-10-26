// This function creates a new node from external data
var newNodeExternal = function(name, type, id, x, y, instance, outputlabel){
  
  if(outputlabel !== ''){instance.data.outputlabels[id] = outputlabel;}
  //console.log(outputlabel)
  //console.log(instance.data.outputlabels[id])
  //var id = id; //name.split(' ').join('_')//jsPlumbUtil.uuid();
  var d = $('<div>').attr('id', id).addClass('w ' + type);
  var title =  $('<div>').addClass('title').text(name);

  d.append(title);

  var canvas = $("#sandbox_container");
  canvas.append(d);

  d.css('left', x + "px");
  d.css('top', y + "px");

  return d;
};



var initNode = function(el, instance) {

            var i = instance;
            // initialise draggable elements.
            instance.draggable(el, {
              grid: [0.5,0.5],
              containment:true,
            });
};