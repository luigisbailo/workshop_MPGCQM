import numpy as np
import pandas as pd
import ase.io
import os
from bokeh.util.browser import view
from bokeh.layouts import column, row, Spacer
from bokeh.models import CustomJS, ColumnDataSource, Select, Slider, DataTable, TableColumn, CDSView, IndexFilter, Paragraph
from bokeh.models import ColorBar, BasicTicker, LinearColorMapper, HoverTool, TapTool, Rect, PreText
from bokeh.plotting import figure, output_file, output_notebook, show, reset_output
from bokeh.palettes import Greys256, Inferno256, Magma256, Plasma256, Viridis256, Cividis256, Spectral
from bokeh.embed import components, file_html
from bokeh.resources import CDN
from colorcet import colorwheel

def toColor(data):
    data -= min(data)
    if (max(data) == 0): return [128 for i in data] #if the every item in input data was equal
    data *= 255/max(data)
    return [int(round(num)) for num in data]

def toSize(data):
    MEDIAN_POINT_SIZE = 10
    DEVIATION = 5

    mid = (max(data) - min(data))/2 + min(data)
    new_data = [i - mid for i in data]

    max_element = max(new_data)

    if (max_element == 0): return [MEDIAN_POINT_SIZE for i in new_data] #if the every item in input data was equal

    new_data = [DEVIATION/max_element * i + MEDIAN_POINT_SIZE for i in new_data]

    return new_data

def MakeStructFiles(structure_filenames, file_format):
    path = 'structures'
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        print ("The directory %s was not created (most likely because the directory already existed)" % path)
    atoms_list = [ase.io.read(filename, format=file_format) for filename in structure_filenames]
    for i in range(len(atoms_list)):
        ase.io.write("structures/set" + str(i) + ".xyz", atoms_list[i])

def LayoutMaker(data_df, structure_filenames=[], log_string='No Log File', palette_name='Viridis256',
                file_format='aims', create_files=True, img_filenames=None, x_index=0, y_index=1,
                color_index=2, size_index=3):

    #Constants
    NONE_COLOR = 'lightskyblue'
    NONE_SIZE = 10
    PLOT_DIMENSION = 500
    OVERVIEW_PLOT_DIMENSION = 200
    PLOT_RATIO = PLOT_DIMENSION/OVERVIEW_PLOT_DIMENSION
    SELECT_WIDTH = 100
    TABLE_HEIGHT = 200

    #Convert structure files for jmol
    if create_files and structure_filenames != [] and structure_filenames != None:
        print("Making structure files for visualizer...")
        MakeStructFiles(structure_filenames, file_format)
    elif create_files == False:
        print("Warning, create_files set to false, this could cause errors with jmol visulization")

    #Make a copy of data_df for the table later & make all column names strings
    original_df = data_df.copy()
    data_df = data_df.copy()
    data_df.columns = data_df.columns.astype('str')
    table_df = data_df.copy()

    #Adjusted for catagorical data
    print("Adjusting in case of non-numerical data...")
    for col in data_df.columns:
        if (data_df[col].dtype == 'object'):
            log_string += '\n' + "Changing column " + col + " of type " + type(data_df[col][0]).__name__ + " to catagorical."
            labels = data_df[col].astype('category').cat.categories.tolist()
            replacement_map = {col : {k: v for k,v in zip(labels,list(range(1,len(labels)+1)))}}
            data_df.replace(replacement_map, inplace=True)

    #Color Data
    color_df = data_df.copy()
    for col in color_df.columns:
        color_df[col] = toColor(color_df[col])
    color_df['None'] = NONE_COLOR

    #Size Data
    size_df = data_df.copy()
    for col in size_df.columns:
        size_df[col] = toSize(size_df[col])
    size_df['None'] = NONE_SIZE

    #Palette Dictionary & Make 8 Color Palette
    EightColorPalette = []
    pal = Spectral[8]
    for i in range (0,256):
        if i/32 < 1: EightColorPalette += [pal[0]]
        elif i/32 < 2: EightColorPalette += [pal[1]]
        elif i/32 < 3: EightColorPalette += [pal[2]]
        elif i/32 < 4: EightColorPalette += [pal[3]]
        elif i/32 < 5: EightColorPalette += [pal[4]]
        elif i/32 < 6: EightColorPalette += [pal[5]]
        elif i/32 < 7: EightColorPalette += [pal[6]]
        else: EightColorPalette += [pal[7]]

    PALETTE_DICT = {'Greys256':Greys256, 'Inferno256':Inferno256,'Magma256':Magma256,
                    'Plasma256':Plasma256, 'Viridis256':Viridis256, 'Cividis256':Cividis256,
                    'EightColorPalette':EightColorPalette, 'Periodic':colorwheel}




    #Plot Data
    plot_df = pd.DataFrame(columns=['x', 'y', 'c', 's'])

    plot_df['x'] = data_df.iloc[:,x_index]
    plot_df['y'] = data_df.iloc[:,y_index]

    if (color_index == None or color_index >= data_df.columns.size):
        color_index = data_df.columns.size
        plot_df['c'] = NONE_COLOR
    else:
        plot_df['c'] = [PALETTE_DICT[palette_name][index] for index in color_df.iloc[:,color_index]]

    if (size_index == None or size_index >= data_df.columns.size):
        size_index = data_df.columns.size
        plot_df['s'] = NONE_SIZE
    else:
        plot_df['s'] = size_df.iloc[:,size_index]

    plot_df['os'] = plot_df['s']/PLOT_RATIO

    if (img_filenames is not None): plot_df['imgs'] = img_filenames

    for col in data_df.columns:
        if col not in plot_df.columns:
            plot_df[col] = original_df[col]
        else:
            plot_df[col + 'Original'] = original_df[col]

    #Convert to sources
    plotsrc  = ColumnDataSource(plot_df)
    datasrc  = ColumnDataSource(data_df)
    colorsrc = ColumnDataSource(color_df)
    sizesrc  = ColumnDataSource(size_df)
    tablesrc = ColumnDataSource(table_df)




    #Make tools for plot
    tool_divs = []
    for col in plot_df.columns:
        if col not in ['x', 'y', 'c', 's', 'os', 'imgs']:
            tool_divs += ['<div> <span style="font-size: 10px; color: royalblue;">%s</span> <span style="font-size: 10px;"> = @{%s}</span> </div>'%(col, col)]
    img_div = '''
    <div>
        <img
            src="@imgs" height="56" alt="@imgs" width="56"
            style="display: table; margin: 0 auto;"
            border="2"
        ></img>
    </div>
    '''
    tooltips = '<div>'
    if (img_filenames is not None): tooltips += img_div
    for div in tool_divs: tooltips += div
    tooltips += '</div>'

    hover = HoverTool(tooltips=tooltips)
    tools=["tap", "box_zoom", "pan", "reset", 'wheel_zoom', 'lasso_select', 'save', hover]




    #Make the plot
    print("Creating plot, table, and jmol...")
    plot = figure(tools=tools, plot_width=PLOT_DIMENSION+50, plot_height=PLOT_DIMENSION, toolbar_location='above')
    circle = plot.circle(x='x', y='y', source=plotsrc, fill_color='c', line_color='c', size='s',
                fill_alpha=0.7, line_alpha = None, hover_fill_color="firebrick", hover_line_color='firebrick')
    tooltips = []
    for col in plot_df.columns:
        if col not in ['x', 'y', 'c', 's', 'os']:
            tooltips += [(col, '@{' + col + '}')]
    # hover = HoverTool(tooltips=tooltips, renderers=[circle], mode='mouse')
    # plot.add_tools(hover)

    if(data_df.columns.size > 2 and palette_name != 'EightColorPalette'):
        cmin = min(data_df.iloc[:,2])
        cmax = max(data_df.iloc[:,2])
        color_bar_visible = True
    else:
        cmin = 1
        cmax = 100
        color_bar_visible = False

    color_mapper = LinearColorMapper(palette=PALETTE_DICT[palette_name], low=cmin, high=cmax)
    color_bar = ColorBar(color_mapper=color_mapper, ticker=BasicTicker(), label_standoff=4, border_line_color=None,
                        location=(0,0), orientation="vertical", background_fill_alpha=0, border_line_alpha=0, width=20)
    color_bar.visible = color_bar_visible

    plot.add_layout(color_bar, 'left')
    plot.grid.grid_line_alpha = 0.5
    plot.axis.axis_line_alpha = 0.2
    plot.axis.major_tick_line_alpha = 0.2
    plot.axis.minor_tick_line_alpha = 0.2
    plot.outline_line_color = None
    # plot.background_fill_color = "lightskyblue"
    # plot.background_fill_alpha = 0.1

    if(len(data_df) < 2000):
        fraction = 1
        index_list = [i for i in range(len(data_df))]
    else:
        fraction = round(2000/len(data_df), 1)
        if fraction < 0.1: fraction = 0.1
        index_list = np.random.choice(len(data_df), int(fraction*len(data_df)), replace=False)

    view = CDSView(source=plotsrc, filters=[IndexFilter(index_list)])
    circle.view = view

    tap_jscode="""
        var idx_struc = cb_data.source['selected']['1d'].indices;
        if (!Number.isInteger(idx_struc)){idx_struc=idx_struc[0]}
        //var data = source.data;
        //var structure_file = data['structure_filenames'][idx_struc];
        var structure_file = 'structures/set' + idx_struc + '.xyz';
        console.log(structure_file);
        var str = "" + idx_struc;
        //var pad = "000000";
        //var indx = pad.substring(0, pad.length - str.length) + str;
        var indx = str;
        var file= "javascript:Jmol.script(jmolApplet0," + "'set frank off; load " + structure_file + ";')";
        location.href=file;
        localStorage.setItem("indexref",indx);

        var attributes = '';

        for (var i = 0; i < info_list.length; i++) {
            localStorage.setItem(info_list[i], source.data[info_list[i]][indx]);
            attributes += info_list[i] + '<br>';
        }

        localStorage.setItem('attributes', attributes);

        document.getElementById("molecule_text").innerHTML = " Selected molecule ID: "+ idx_struc;
        //document.getElementById("info").innerHTML = "Complete Selection: " + plotdata['id'][ind]  ;
        """
    if (structure_filenames != [] and structure_filenames != None):
        taptool = plot.select(type=TapTool)
        if img_filenames == None: start_col = 5
        else: start_col = 6

        info_list = [col for col in plot_df.columns[start_col:]]
        taptool.callback = CustomJS(args=dict(source=plotsrc, info_list=info_list), code=tap_jscode)




    #Make the second plot to show overview
    overview_plot = figure(tools=[], plot_width=OVERVIEW_PLOT_DIMENSION, plot_height=OVERVIEW_PLOT_DIMENSION)
    overview_circle = overview_plot.circle(x='x', y='y', source=plotsrc, fill_color='c', line_color='c', size='os',
                                            fill_alpha=0.7, line_alpha = None)
    overview_plot.axis.visible = False;
    overview_plot.grid.visible = False;
    overview_plot.outline_line_color = None;
    overview_plot.background_fill_color = "gray"
    overview_plot.background_fill_alpha = 0.1

    overview_jscode="""
        var data = source.data;
        var start = cb_obj.start;
        var end = cb_obj.end;
        data['%s'] = [start + (end - start) / 2];
        data['%s'] = [end - start];
        source.change.emit();
    """
    overviewsrc = ColumnDataSource({'x_range': [], 'y_range': [], 'width': [], 'height': []})
    plot.x_range.callback = CustomJS(args=dict(source=overviewsrc), code=overview_jscode % ('x_range', 'width'))
    plot.y_range.callback = CustomJS(args=dict(source=overviewsrc), code=overview_jscode % ('y_range', 'height'))

    rect = Rect(x='x_range', y='y_range', width='width', height='height', fill_alpha=0.1,
                line_alpha=0.3, line_color='black', fill_color='black')
    overview_plot.add_glyph(overviewsrc, rect)

    overview_circle.view = view;




    #Make selects for the plot
    select_jscode="""
        var plotVals = plotsrc.data;
        var dataVals = datasrc.data;
        plotVals['%s'] = dataVals[cb_obj.value]
        plotsrc.change.emit();
    """

    x_callback = CustomJS(args={"plotsrc":plotsrc, "datasrc":datasrc}, code=select_jscode % 'x')
    y_callback = CustomJS(args={"plotsrc":plotsrc, "datasrc":datasrc}, code=select_jscode % 'y')




    palette_options = list(PALETTE_DICT.keys())

    # if (data_df.columns.size < 3):
    #     size_colnum = 2
    # else:
    #     size_colnum = 3

    palette_select = Select(title='Palette', width=150, value=palette_name, options=palette_options)
    x_select       = Select(options=data_df.columns.tolist(), value=data_df.columns[x_index], title='X-Axis', width=SELECT_WIDTH)
    y_select       = Select(options=data_df.columns.tolist(), value=data_df.columns[y_index], title='Y-Axis', width=SELECT_WIDTH)
    color_select   = Select(options=color_df.columns.tolist(), value=color_df.columns[color_index], title='Color',  width=SELECT_WIDTH)
    size_select    = Select(options=size_df.columns.tolist(), value=size_df.columns[size_index], title='Size',   width=SELECT_WIDTH)


    x_select.js_on_change('value', x_callback)
    y_select.js_on_change('value', y_callback)




    size_jscode="""
        var plotVals = plotsrc.data;
        var sizeVals = sizesrc.data;

        if (cb_obj.value == 'None'){
            for (var i = 0; i < plotVals['s'].length; i++) {
                plotVals['s'][i] = sizesrc.data['None'][i];
                plotVals['os'][i] = sizesrc.data['None'][i]/PLOT_RATIO;
            }
            plotsrc.change.emit();
            return;
        }

        for (var i = 0; i < plotVals['s'].length; i++) {
            plotVals['s'][i] = sizeVals[cb_obj.value][i];
            plotVals['os'][i] = sizeVals[cb_obj.value][i]/PLOT_RATIO;
        }
        plotsrc.change.emit();
    """
    size_callback = CustomJS(args={"plotsrc":plotsrc, "sizesrc":sizesrc, "PLOT_RATIO":PLOT_RATIO}, code=size_jscode)
    size_select.js_on_change('value', size_callback)




    color_jscode="""
        var plotVals = plotsrc.data;
        var ccol = plotVals['c'];

        var colorVals = colorsrc.data;
        var icol = colorVals[cb_obj.value];

        if (cb_obj.value == 'None'){
            for (var i = 0; i < ccol.length; i++) {
                ccol[i] = icol[i]
            }
            plotsrc.change.emit();
            colorBar.visible = false;
            return;
        }

        //Code below updates the color bar
        colorBar.visible = true;
        var dcol = datasrc.data[cb_obj.value]
        var min = dcol[0]
        var max = dcol[0]
        for (var i = 0; i < dcol.length; i++) {
            if (dcol[i] < min) min = dcol[i];
            else if (dcol[i] > max) max = dcol[i];
        }
        if (max == min) {
            min--;
            max++;
        }
        colorBar.color_mapper.low = min
        colorBar.color_mapper.high = max

        //This code takes care of updating the color on the plot
        var palVals = palettesrc.data;
        var palette = palVals[paletteSelect.value];

        for (var i = 0; i < ccol.length; i++) {
            ccol[i] = palette[icol[i]];
        }

        if (paletteSelect.value == 'EightColorPalette') {
            colorBar.visible = false;
        }

        plotsrc.change.emit();
    """

    palettesrc = ColumnDataSource(PALETTE_DICT)
    color_callback = CustomJS(args={"plotsrc":plotsrc, 'datasrc':datasrc, "colorsrc":colorsrc, 'palettesrc':palettesrc,
                            'paletteSelect':palette_select, "colorBar":color_bar},
                        code=color_jscode)

    color_select.js_on_change('value', color_callback)




    palette_jscode="""
        var plotVals = plotsrc.data;
        var ccol = plotVals['c'];

        var colorVals = colorsrc.data;
        var icol = colorVals[colorSelect.value];

        var palVals = palettesrc.data;
        var palette = palVals[cb_obj.value];

        colorBar.color_mapper.palette = palette

        //Don't update color if the color column is set to none
        if (colorSelect.value == 'None') {
            colorBar.visible = false;
            return;
        }

        colorBar.visible = true;

        for (var i = 0; i < ccol.length; i++) {
            ccol[i] = palette[icol[i]];
        }
        if (cb_obj.value == 'EightColorPalette') {
            colorBar.visible = false;
        }
        plotsrc.change.emit();
    """

    palette_callback = CustomJS(args={"plotsrc":plotsrc, "colorsrc":colorsrc, 'palettesrc':palettesrc, 'colorSelect':color_select,
                            "colorBar":color_bar}, code=palette_jscode)

    palette_select.js_on_change('value', palette_callback)




    #Now make the table
    cols = [TableColumn(field=col_name, title=col_name) for col_name in data_df.columns]
    data_table = DataTable(columns = cols, source = tablesrc, height = TABLE_HEIGHT)
    if (len(cols) > 8): data_table.fit_columns = False
    data_table.sizing_mode = 'stretch_width'
    # data_table.view = view;




    #Now make the slider
    slider = Slider(start=0, end=len(data_df)-1, value=0, step=1, title='Selected ID', width=300)
#     slider.sizing_mode = 'stretch_width'
    slider_jsmol_code="""
        var idx_struc = cb_obj.value;
        //var data = source.data;
        //var structure_file = data['structure_filenames'][idx_struc]
        var structure_file = 'structures/set' + idx_struc + '.xyz';
        var str = "" + idx_struc;
        //var pad = "000000";
        //var indx = pad.substring(0, pad.length - str.length) + str;
        var indx = str;
        var file= "javascript:Jmol.script(jmolApplet0," + "'set frank off; load " + structure_file + ";')";
        location.href=file;
        localStorage.setItem("indexref",indx);

        var attributes = '';

        for (var i = 0; i < info_list.length; i++) {
            localStorage.setItem(info_list[i], source.data[info_list[i]][indx]);
            attributes += info_list[i] + '<br>';
        }

        localStorage.setItem('attributes', attributes);

        document.getElementById("molecule_text").innerHTML = " Selected molecule ID: "+ idx_struc;
        //document.getElementById("info").innerHTML = "Complete Selection: " + plotdata['id'][ind]  ;
        """
    if (structure_filenames != [] and structure_filenames != None):
        slider.js_on_change('value', CustomJS(args=dict(source=plotsrc, info_list=info_list), code=slider_jsmol_code))



    #Very important to link up the selections from table, slider, and plot correctly:
        #First, we make the javascript code for the slider and plotsrc
    slider_jscode = """
        tablesrc.selected.indices = [cb_obj.value];
        tablesrc.change.emit();
    """
    plotsrc_selected_jscode = """
        if (cb_obj.indices.length == 0 || cb_obj.indices[0] == null) {
            return;
        }
        slider.value = cb_obj.indices[0];
    """

        #Second, we make the callbacks and add them to the slider and the plotsrc
    plotsrc_selected_callback = CustomJS(args={"slider":slider}, code=plotsrc_selected_jscode)
    plotsrc.selected.js_on_change('indices', plotsrc_selected_callback)

    slider_callback = CustomJS(args={"tablesrc":tablesrc}, code=slider_jscode)
    slider.js_on_change('value', slider_callback)

        #Third, we link up the slider, datasrc, and plotsrc

    slider.js_on_change('value', slider_callback)                        #Slider hooks up to the datasrc (table)
    tablesrc.selected.js_link('indices', plotsrc.selected, 'indices')     #Datasrc (table) hooks up to the plotsrc (plot)
    plotsrc.selected.js_on_change('indices', plotsrc_selected_callback)  #Plotsrc (plot) hooks up to the slider




    #Now we make the fraction of data slider
    fraction_slider = Slider(start=.1, end=1, value=fraction, step=.1, title='Fraction of Loaded Data', width=300)
#     fraction_slider.sizing_mode = 'stretch_width'

    #For some reason bokeh only triggers the filter change if the actual filter changes, not just the indices
    #So we have to make two filters and alternate between them. (Not the prettiest, but it works)
    filt1 = IndexFilter([])
    filt2 = IndexFilter([])
    fraction_slider_jscode = """
        if (view.filters[0] == filt2) {
            temp = filt1;
        }
        else {
            temp = filt2;
        }
        temp.indices = [];


        for (var i = 0; i < high; i++) temp.indices.push(i);

        for (var i = 0; i < (1-cb_obj.value)*high; i++) {
            temp.indices.splice(Math.floor(Math.random() * temp.indices.length), 1);
        }

        view.filters = [temp];
    """
    fraction_slider_callback = CustomJS(args={'view':view, 'table':data_table, "filt1":filt1, 'filt2':filt2,
                                              'high':len(data_df)}, code=fraction_slider_jscode)
    fraction_slider.js_on_change('value', fraction_slider_callback)




    #Now we make the point alpha slider
    alpha_slider = Slider(start=.1, end=1, value=0.7, step=.05, title='Point-Alpha', width=200)
    alpha_slider.js_link('value', circle.glyph, 'fill_alpha')
    alpha_slider.js_link('value', overview_circle.glyph, 'fill_alpha')




    #Now make the paragraph for the log file
    paragraph = PreText(text=log_string, width=200, height=100)
    paragraph.sizing_mode = 'stretch_width'



    #Put it all together in a layout and return the newly created layout
    spacer = Spacer(width=38)
    select_row = row(x_select, y_select, color_select, size_select, palette_select)
    slider_row = row(fraction_slider, spacer, alpha_slider, spacer, slider)
    plot_row = row(plot, spacer, overview_plot)
    layout = column(select_row, slider_row, plot_row, data_table, paragraph)
    layout.sizing_mode = 'stretch_both'

    return layout

def Visualize(data_df, structure_filenames=[], log_string='No Log File', palette_name='Viridis256',
              file_format='aims', create_files=True, img_filenames=None, x_index=0, y_index=1,
              color_index=2, size_index=3):

    layout = LayoutMaker(data_df, structure_filenames, log_string, palette_name,
                        file_format, create_files, img_filenames, x_index, y_index,
                        color_index, size_index)

    if (structure_filenames == [] or structure_filenames == None):
        print("The interface will not have jmol because no structure_filenames were passed in")
        page = file_html(layout, CDN)
        with open('./visualize.html', 'w') as f:
            f.write(page)
        view('./visualize.html')
        return

    script, div = components(layout)

    page = '''<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="X-UA-Compatible" content="ie=edge">
            <title>Visualizer</title>

            <link rel="stylesheet" href="https://cdn.pydata.org/bokeh/release/bokeh-1.1.0.min.css" type="text/css" />
            <link rel="stylesheet" href="https://cdn.pydata.org/bokeh/release/bokeh-widgets-1.1.0.min.css" type="text/css" />
            <link rel="stylesheet" href="https://cdn.pydata.org/bokeh/release/bokeh-tables-1.1.0.min.css" type="text/css" />

            <script type="text/javascript" src="https://cdn.pydata.org/bokeh/release/bokeh-1.1.0.min.js"></script>
            <script type="text/javascript" src="https://cdn.pydata.org/bokeh/release/bokeh-widgets-1.1.0.min.js"></script>
            <script type="text/javascript" src="https://cdn.pydata.org/bokeh/release/bokeh-tables-1.1.0.min.js"></script>
            <script type="text/javascript">Bokeh.set_log_level("info");</script>

            <script type="text/javascript" src="JSmol.min.js"></script>
            <script type="text/javascript" src="myjsmol.js"></script>

            <script type="text/javascript">
               inds="0" ;      // initialization of the local storage used in popup window
               localStorage.setItem("indexref",inds);
               localStorage.setItem("attributes",'');
            </script>

            <style>
                #jsmol {
                    position:absolute;
                    top:30px;
                    left:800px;
                    /* left:750px; */
                    text-align:center;
                    font-family: Arial, Helvetica, sans-serif;
                    font-weight: normal;
                }

                .button {
                    cursor:pointer;
                    margin:12px;
                    width: 80px;
                    /* margin-left: 100px; */
                    background-color:#28AE7F;
                    border:none;
                    display:inline-block;
                    border-radius:4px;
                    color:white;
                    padding:20px 0;
                    text-align:center;
                    text-decoration:none;
                }

                #analyze {
                    margin-left: 20%%;
                }

                .button:hover {
                    background-color: #2A768E;
                    color:white;
                    -o-transition:.2s;
                    -ms-transition:.2s;
                    -moz-transition:.2s;
                    -webkit-transition:.2s;
                  /* ...and now for the proper property */
                    transition:.2s;
                }

                #appdiv {
                    width:450px;
                    /* width:500px; */
                    height:450px
                }

                #molecule_text {
                    margin:5px;
                    margin-right:20px;
                    margin-bottom:0;
                    padding:4px 0;
                    color:white;
                    background-color:gray;
                    border-radius:4px;
                }

                #radio_group {
                    margin-top: 5px;
                    position: relative;
                }

                #jmolRadioGroup0 input {
                    position: relative;
                    opacity: 0.5;
                    cursor: pointer;
                }

                #jsmol_hold {
                    position:absolute;
                    top:316px;
                    left:550px;
                    text-align:center;
                    font-family: Arial, Helvetica, sans-serif;
                    font-weight: normal;
                }
            </style>

            %s

        </head>
        <body>
            <div class=wrapper style="position:relative;">
                %s
                <div id='jsmol_hold'>
                    <iframe name='compare' width="250" height="275" frameborder="0" > </iframe>
                </div>
                <div id='jsmol'>
                    <button class='button' id='analyze' href="javascript:void(0);" onclick='cloneJSmol(jmolApplet0);'> <span>Analyze </span></button>
                    <button class="button" id='hold' href="javascript:void(0);"  onclick='holdJSmol(jmolApplet0);'><span>Hold </span> </button>
                    <div id="appdiv"></div>
                    <!--<div id='radio_group'>
                        <script>
                          Jmol.jmolHtml("<b>Spin:</b> ");
                          Jmol.jmolRadioGroup('jmolApplet0',[
                            ['set spinX 10; set spinY 0; set spinZ 0; spin on;', 'X'],
                            ['set spinX 0; set spinY 10; set spinZ 0; spin on;', 'Y'],
                            ['set spinX 0; set spinY 0; set spinZ 10; spin on;', 'Z'],
                            ['spin off;', 'Off', 'checked'] ], '&nbsp;&nbsp;');
                        </script>
                    </div>-->
                    <div id="molecule_text" > Selected molecule ID: 0</div>
                </div>
            </div>
        </body>
        </html>
    ''' % (script, div)

    print('Writing file dependencies...')

    with open('./visualize.html', 'w') as f:
        f.write(page)

    writePop()
    writeCompare()
    writeMyJmol()

    view('./visualize.html')

    print('Done.')

def writeCompare():
    page = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="Author" content="Sandip De" />
    <title>The Jmol Viewer</title>
    <script type="text/javascript" src="JSmol.min.js"></script>
    <style type="text/css">
    /* These are important, dont change: */

    html, body {font-family:Arial, Helvetica, sans-serif; height: 100%; overflow: hidden; margin: 0; padding: 0; }
    .JmolPanels { position: absolute; overflow: hidden; }
    .textPanels { position: absolute; overflow: auto; }

    /* Dont add margin nor padding to textPane; if needed, use an inner div with desired style (like contents below) */

    /* These are aesthetic, can be customized: */

    .content {
      padding: 0.2em 1ex;
      padding-top: 0.3em;
    }

    #hold_text {
      padding: 4px 15px;
      font-weight:normal;
      /* margin-right:30%; */
      color:white;
      background-color:gray;
      border-radius:4px;
    }
    </style>

    <script type="text/javascript">
    //  	USER'S SETTINGS:
    // sets the side of the page that the model appears on,you can set this to "top" or "bottom"
    var side = "top"
    // you can set this to any integer, meaning percent of window height assigned to Jmol panel
    var h = 90; //Alex changed this from 80
    //      --------------

    var cssTx = '<style type="text/css">'
    cssTx += '#JmolPane  { left:0px; width:100%; top:' + ( (side=="top") ? "0px" : ((100-h)+"%") ) + '; height:' + h + '%;} '
    cssTx += '#mainPane  { text-align: center; left:0px; width:100%; top:' + ( (side=="top") ? (h+"%") : "0px" ) + '; height:' + (100-h) + '%;} '
    cssTx += '</style>'
    document.writeln(cssTx)

    var jmolAppletA;

    // logic is set by indicating order of USE -- default is HTML5 for this test page, though
    var use = "HTML5" // JAVA HTML5 WEBGL IMAGE  are all otions
    var s = document.location.search;

    Jmol.debugCode = (s.indexOf("debugcode") >= 0);

    var xxxx = document.location.search

    var Info0 = {
      width:  "100%",
      height: "100%",
      use: "HTML5",
      debug: false,
      color: "0xFFFFFF",
      j2sPath: "./j2s", // this needs to point to where the j2s directory is.
      jarPath: "./jsmol/java",// this needs to point to where the java directory is.
      jarFile: "./jsmol/JmolAppletSigned.jar",
      isSigned: true,
      serverURL: "./jsmol/php/jsmol.php",
      script: opener.JSmolCloneData.state.replace(/zoomLarge true/i,'zoomLarge false'),
      use: opener.JSmolCloneData.type ,
      disableJ2SLoadMonitor: true,
      disableInitialConsole: true,
      allowJavaScript: true
    };
    var inds=localStorage.getItem("index");
    </script>
    </head>

    <body>

    <div id="JmolPane" class="JmolPanels">
    <script type="text/javascript">
      jmolAppletA = Jmol.getApplet("jmolAppletA", Info0)
      Jmol.script(JSmolClone,"set platformSpeed " + opener.JSmolCloneData.platformSpeed);
    </script>
    </div>

    <div id="mainPane" class="textPanels">
    	<div class="content">
    <script type="text/javascript">
      if (inds != null) Jmol.jmolHtml("<b id='hold_text'> Selected ID: "+ inds +"</b> <br> ");
    </script>
    <!--br />&copy; 2017 <a href="mailto:1sandipde@gmail.com">Sandip De</a-->
    	</div> <!--content-->
    </div> <!--mainPane-->
    </body>
    </html>'''

    with open('compare.html', 'w') as f:
        f.write(page)

def writePop():
    page = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="Author" content="Sandip De" /> <!-- adjusted by Alex Shaw-->
    <title>The Jmol Viewer</title>
    <script type="text/javascript" src="JSmol.min.js"></script>
    <style type="text/css">
    /* These are important, dont change: */

    html, body { font-family:Arial, Helvetica, sans-serif; height: 100%; overflow: hidden; margin: 0; padding: 0; }
    .JmolPanels { position: absolute; overflow: hidden; }
    .textPanels { position: absolute; overflow: auto; }

    /* Dont add margin nor padding to textPane; if needed, use an inner div with desired style (like contents below) */

    /* These are aesthetic, can be customized: */

    .content { padding: 0.5em 1ex; }
    </style>

    <script type="text/javascript">
    //  	USER'S SETTINGS:
    // sets the side of the page that the model appears on,you can set this to "top" or "bottom"
    var side = "top"
    // you can set this to any integer, meaning percent of window height assigned to Jmol panel
    var h = 80
    //      --------------

    var cssTx = '<style type="text/css">'
    cssTx += '#JmolPane  { left:0px; width:100%; top:' + ( (side=="top") ? "0px" : ((100-h)+"%") ) + '; height:' + h + '%;} '
    cssTx += '#mainPane  { left:0px; width:100%; top:' + ( (side=="top") ? (h+"%") : "0px" ) + '; height:' + (100-h) + '%;} '
    cssTx += '</style>'
    document.writeln(cssTx)

    var jmolAppletA;

    // logic is set by indicating order of USE -- default is HTML5 for this test page, though
    var use = "HTML5" // JAVA HTML5 WEBGL IMAGE  are all otions
    var s = document.location.search;

    Jmol.debugCode = (s.indexOf("debugcode") >= 0);

    var xxxx = document.location.search

    var Info0 = {
      width:  "100%",
      height: "100%",
      use: "HTML5",
      debug: false,
      color: "0xFFFFFF",
      j2sPath: "./j2s", // this needs to point to where the j2s directory is.
      jarPath: "./jsmol/java",// this needs to point to where the java directory is.
      jarFile: "./jsmol/JmolAppletSigned.jar",
      isSigned: false,
      serverURL: "./jsmol/php/jsmol.php",
      script: opener.JSmolCloneData.state.replace(/zoomLarge true/i,'zoomLarge false'),
      use: opener.JSmolCloneData.type ,
      disableJ2SLoadMonitor: true,
      disableInitialConsole: true,
      allowJavaScript: true
    };
    var inds=localStorage.getItem("index");
    var attributes=localStorage.getItem('attributes').split("<br>");
    if (attributes.length != 0 && attributes[attributes.length - 1] == '') attributes.splice(attributes.length - 1,1);
    </script>
    </head>

    <body>

    <div id="JmolPane" class="JmolPanels">
    <script type="text/javascript">
      jmolAppletA = Jmol.getApplet("jmolAppletA", Info0)
      Jmol.script(JSmolClone,"set platformSpeed " + opener.JSmolCloneData.platformSpeed);
    </script>
    </div>

    <div id="mainPane" class="textPanels">
    	<div class="content">
    <script type="text/javascript">
      Jmol.jmolHtml('<span> Selected molecule ID: '+ inds +"</span> <br> ");
      Jmol.jmolHtml("<b>Schemes:</b> ");
      Jmol.jmolRadioGroup(jmolAppletA,[
          ['cartoons off; trace off; rockets off; select visible; spacefill 20%; wireframe 0.15;', 'Ball &amp; Stick', 'checked'],
          ['cartoons off; trace off; rockets off; select visible; spacefill 0%; wireframe 0.15;', 'Tube'],
          ['cartoons off; trace off; rockets off; select visible; spacefill 0%; wireframe 0.05;', 'Wireframe'],
          ['cartoons off; trace off; rockets off; select visible; spacefill 100%; wireframe 0.05;', 'Space filling'],
          ], '&nbsp;&nbsp;', 'scheme1');
      Jmol.jmolHtml("<br> <b>Measure:</b> ");
      Jmol.jmolRadioGroup(jmolAppletA,[
          ['set measurement ANGSTROMS; set picking MEASURE DISTANCE; set pickingStyle MEASURE ON;', 'Distance'],
          ['set picking MEASURE ANGLE; set pickingStyle MEASURE ON;', 'Angle'],
          ['set picking MEASURE TORSION; set pickingStyle MEASURE ON;', 'Torsion'],
          ['set pickingStyle MEASURE OFF;', 'Off', 'checked'] ], '&nbsp;&nbsp;');
      Jmol.jmolHtml("&nbsp;&nbsp;&nbsp;<b>3D:</b> ");
      Jmol.jmolMenu(jmolAppletA,[
          ['background black; stereo off;', ' Stereo 3D off ', 'checked'],
          ['background grey; stereo REDCYAN;', 'Red / Cyan'],
          ['background grey; stereo REDBLUE;', 'Red / Blue'],
          ['background grey; stereo REDGREEN;', 'Red / Green'],
          ['background grey; stereo -5;', 'Cross-eyed'],
          ['background grey; stereo 5;', 'Wall-eyed']
          ], '1');
      Jmol.jmolHtml("<br /><b>Spin:</b> ");
      Jmol.jmolRadioGroup(jmolAppletA,[
          ['set spinX 10; set spinY 0; set spinZ 0; spin on;', 'X'],
          ['set spinX 0; set spinY 10; set spinZ 0; spin on;', 'Y'],
          ['set spinX 0; set spinY 0; set spinZ 10; spin on;', 'Z'],
          ['spin off;', 'Off', 'checked'] ], '&nbsp;&nbsp;');
      Jmol.jmolHtml("<br><br>");
      for (var i = 0; i < attributes.length; i++) {
        Jmol.jmolHtml("<b>" + attributes[i] + '</b><span> = ' + localStorage.getItem(attributes[i]) + "</span> <br> ");
      }
    </script>
    <!--br />&copy; 2017 <a href="mailto:1sandipde@gmail.com">Sandip De</a-->
    	</div> <!--content-->
    </div> <!--mainPane-->
    </body>
    </html>'''

    with open('pop.html', 'w') as f:
        f.write(page)

def writeMyJmol():
    page = '''
    Jmol._isAsync = false;
    var jmolApplet0; // set up in HTML table, below
    jmol_isReady = function(applet) {
    // document.title = (applet._id + " - Jmol " + Jmol.___JmolVersion)
    // Jmol._getElement(applet, "appletdiv").style.border="10px solid blue"
    }

    var Info = {
       width: '100%',
       height: '100%',
       debug: false,
       color: "0xFFFFFF",
       use: "HTML5",   // JAVA HTML5 WEBGL are all options
       j2sPath: "./j2s", // this needs to point to where the j2s directory is.
       jarPath: "./jsmol/java",// this needs to point to where the java directory is.
       jarFile: "./jsmol/JmolAppletSigned.jar",
       isSigned: true,
       script: "set antialiasDisplay; set frank off; load structures/set0.xyz" ,
       serverURL: "./jsmol/php/jsmol.php",
       readyFunction: jmol_isReady,
       disableJ2SLoadMonitor: true,
       disableInitialConsole: true,
       allowJavaScript: true
    };


    $(document).ready(function() {
       $("#appdiv").html(Jmol.getAppletHtml("jmolApplet0", Info))
    });
    var lastPrompt=0;

    var JSmolCloneData = {};
    function cloneJSmol(JSmolObject) {
      var t = JSmolObject._jmolType; //temp
      if ( /_Canvas2D/.test(t) ) { t = 'HTML5'; }
      else if ( /_Canvas3D/.test(t) ) { t = 'WebGL'; }
      else if ( /_Applet/.test(t) ) { t = 'Java'; }
      else { t = null; }
      JSmolCloneData.type = t;
      JSmolCloneData.platformSpeed = Jmol.evaluate(JSmolObject, 'platformSpeed + 0');
      JSmolCloneData.state = Jmol.getPropertyAsString(JSmolObject, 'stateInfo');
      var inds=localStorage.getItem("indexref") ;
      localStorage.setItem("index",inds);
      myWindow=window.open('pop.html',inds,'resizable, width=800, height=800, scrollbars, menubars=no, titlebar=no,toolbar=no,location=no,status=yes');

    };


    var inds=localStorage.getItem("index");

    function holdJSmol(JSmolObject){
       console.log("getting hold called");
       var t = JSmolObject._jmolType; //temp
       JSmolCloneData.type = 'HTML5';
       JSmolCloneData.state = Jmol.getPropertyAsString(JSmolObject, 'stateInfo');
       myWindow=window.open('compare.html','compare','width=200, height=200, scrollbars, menubars=no');
       var inds=localStorage.getItem("indexref") ;
       localStorage.setItem("index",inds);

    };'''
    with open('myjsmol.js', 'w') as f:
        f.write(page)
