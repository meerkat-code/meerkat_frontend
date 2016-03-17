
//Takes two categories and collects data from the api.
//It then turns the data turns it into a two dimensional array.
//Any optional analysis (stripping records/colouring/graphing) can then be applied.
//Details for this analysis are given in the options object.
//Finally the table is drawn. 
function createCrossPlot( catx, caty, options ){

	//These variable will hold all the JSON data from the api, when the AJAX requests are complete.
	var queryData, catxData, catyData;

	//Assemble an array of AJAX calls 
	var deferreds = [
		$.getJSON( api_root + '/query_category/' + caty + '/' + catx + '?use_ids=1', function(data) {
			queryData = data;
		}),
		$.getJSON( api_root + "/variables/" + catx, function(data) {
			catxData = data;
		}),
		$.getJSON( api_root + "/variables/" + caty, function(data) {
			catyData = data;
		})
	];

	//Run the AJAX reuqests asynchronously and act when they have all completed.
	$.when.apply( $, deferreds ).then(function() {


		if( $.isEmptyObject(queryData) ){
			console.log("Empty object");
			$('.exploreChart .table-responsive').html( 
				"Unfortunately we can't plot that table.  Please try another combination of categories." 
			);
		}else{

			//Store the variable id's for each category.
			var yKeys = Object.keys(queryData);
			var xKeys = Object.keys(queryData[yKeys[0]]);

			//Get the "names" corresponding to each variable ID in the x category.
			//These names, preceeded by an empty box, form the top row of the table.
			var xKeyNames = ["#Cases"];
			for( var k in xKeys ){
				xKeyNames.push( catxData[xKeys[k]].name );
			}
			var table = [ xKeyNames ];

			//For each key in the y category, form the row from x category data.
			for( var y in yKeys ){
			
				var yKey = yKeys[y];
			
				//Each row begins with the variable name.
				var row = [catyData[yKey].name];

				//The rest of the row are the correctly ordered data points.
				for( var x in xKeys ){

					var xKey = xKeys[x];
					var datum = queryData[yKey][xKey];				
								
					row.push( datum );		
				
				}

				table.push( row );

			}
		
			//Now that we have the data in a form javascript can understand, we can do fancy stuff with it.
			if( options ){
				if( options.strip ) table = strip( table, options.strip );
				if( options.colour == "true" ) table = colour( table );
			}

			//Draw!
			drawCrossPlot( table );
		}
	});
}

//A function that colours the table, to help bring out patterns and information.
function colour( jsTable ){

	//First find the highest and lowest values in the table. 
	var list = [];
	for( var r=1; r<jsTable.length; r++ ){
		row = jsTable[r].slice();
		row.shift();
		list = list.concat( row );
	}

	var maximum = Math.max.apply( Math, list );
	var minimum = Math.min.apply( Math, list );

	for( var y=1; y< jsTable.length; y++ ){
		for( var x=1; x<jsTable[y].length; x++ ){
			var perc = (jsTable[y][x]-minimum)/(maximum-minimum);
			jsTable[y][x] = [ jsTable[y][x], perc ]; 
		}	
	}

	return jsTable;

}

function drawCrossPlot( jsTable ){

	var table = "<table class='table table-hover'>";

	//We draw html tables by rows, not columns, so begin by looping through y.
	for( var y in jsTable ){

		var row = jsTable[y];

		//If first row, draw as headers.
		if( Number(y) === 0 ){
			table += "<tr>";
			for( var h in row ){
				if( Number(h) === 0 ) table += "<th class='header'>" + row[h] + "</th>";
				else table += "<th>" + row[h] + "</th>";
			}
			table += "</tr>";
		}else{

			table += "<tr><td class='header'>" + row[0] + "</td>";
			//Loop through x, drawing a new cell for each data point.
			for( var x=1; x<row.length; x++ ){
				//If this is a three dimensional data set, use colour to indicate the third dimension.
				if( jsTable[y][x].constructor === Array ){
					table += "<td style='background-color:rgba(217, 105, 42, " + 
					         jsTable[y][x][1] + ")'>" + jsTable[y][x][0] + "</td>";
				}else{
					table += "<td>" + jsTable[y][x] + "</td>";
				}
			}
			table += "</tr>";

		}

	} 

	table += "</table>";
	
	$('.exploreChart .table-responsive').html(table);

}

function transpose( jsTable ){
	var newTable = jsTable[0].map(function(col, i) { 
		return jsTable.map(function(row) { 
			return row[i]; 
		});
	});
	return newTable;
}

function strip( table, axis ){

	function stripRows(jsTable){
		//Store a list of rows to be removed.
		var remove = [];

		//For each row iterate through it's elements to seeif all are empty.
		for( var y=1; y<jsTable.length; y++ ){

			var row = jsTable[y].slice();
			row.shift();
			var empty = true;
			
			for( var x in row ){
				if( Number(row[x]) !== 0 ) empty = false;
			}
			if( empty ) remove.push(y);
		}
		//Remove all empty rows (starting from the last to avoid screwing up indexes).
		for( var i = remove.length-1; i>=0; i-- ) jsTable.splice( remove[i], 1 );

		return jsTable;
	}


	if( axis.indexOf('y') != -1 || axis.indexOf('Y') != -1 ){
		table = stripRows( table );
	}
	
	if( axis.indexOf('x') != -1 || axis.indexOf('X') != -1 ){
		table = transpose( stripRows( transpose( table ) ) );
	}
	
	return table;

}


