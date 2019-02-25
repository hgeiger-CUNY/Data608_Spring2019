#!/usr/bin/env python
# coding: utf-8

# In[21]:


import datashader as ds
import datashader.transfer_functions as tf
import datashader.glyphs
from datashader import reductions
from datashader.core import bypixel
from datashader.utils import lnglat_to_meters as webm, export_image
from datashader.colors import colormap_select, Greys9, viridis, inferno
import copy


from pyproj import Proj, transform
import numpy as np
import pandas as pd
import urllib
import json
import datetime
import colorlover as cl

import plotly.offline as py
import plotly.graph_objs as go
from plotly import tools

from shapely.geometry import Point, Polygon, shape
# In order to get shapley, you'll need to run [pip install shapely.geometry] from your terminal

from functools import partial

from IPython.display import GeoJSON

import math
from datashader.bokeh_ext import create_categorical_legend # legend
from bokeh.io import output_notebook, show

py.init_notebook_mode(connected=True)


# For module 2 we'll be looking at techniques for dealing with big data. In particular binning strategies and the datashader library (which possibly proves we'll never need to bin large data for visualization ever again.)
# 
# To demonstrate these concepts we'll be looking at the PLUTO dataset put out by New York City's department of city planning. PLUTO contains data about every tax lot in New York City.
# 
# PLUTO data can be downloaded from [here](https://www1.nyc.gov/assets/planning/download/zip/data-maps/open-data/nyc_pluto_17v1_1.zip). Unzip them to the same directory as this notebook, and you should be able to read them in using this (or very similar) code. Also take note of the data dictionary, it'll come in handy for this assignment.

# In[22]:


# Code to read in v17, column names have been updated (without upper case letters) for v18

# bk = pd.read_csv('PLUTO17v1.1/BK2017V11.csv')
# bx = pd.read_csv('PLUTO17v1.1/BX2017V11.csv')
# mn = pd.read_csv('PLUTO17v1.1/MN2017V11.csv')
# qn = pd.read_csv('PLUTO17v1.1/QN2017V11.csv')
# si = pd.read_csv('PLUTO17v1.1/SI2017V11.csv')

# ny = pd.concat([bk, bx, mn, qn, si], ignore_index=True)

ny = pd.read_csv('pluto_18v2.csv')


# Getting rid of some outliers
ny = ny[(ny['yearbuilt'] > 1850) & (ny['yearbuilt'] < 2020) & (ny['numfloors'] != 0)]


# I'll also do some prep for the geographic component of this data, which we'll be relying on for datashader.
# 
# You're not required to know how I'm retrieving the lattitude and longitude here, but for those interested: this dataset uses a flat x-y projection (assuming for a small enough area that the world is flat for easier calculations), and this needs to be projected back to traditional lattitude and longitude.

# In[23]:


wgs84 = Proj("+proj=longlat +ellps=GRS80 +datum=NAD83 +no_defs")
nyli = Proj("+proj=lcc +lat_1=40.66666666666666 +lat_2=41.03333333333333 +lat_0=40.16666666666666 +lon_0=-74 +x_0=300000 +y_0=0 +ellps=GRS80 +datum=NAD83 +to_meter=0.3048006096012192 +no_defs")
ny['xcoord'] = 0.3048*ny['xcoord']
ny['ycoord'] = 0.3048*ny['ycoord']
ny['lon'], ny['lat'] = transform(nyli, wgs84, ny['xcoord'].values, ny['ycoord'].values)

ny = ny[(ny['lon'] < -60) & (ny['lon'] > -100) & (ny['lat'] < 60) & (ny['lat'] > 20)]

#Defining some helper functions for DataShader
background = "black"
export = partial(export_image, background = background, export_path="export")
cm = partial(colormap_select, reverse=(background!="black"))


# ## Part 1: Binning and Aggregation
# 
# Binning is a common strategy for visualizing large datasets. Binning is inherent to a few types of visualizations, such as histograms and [2D histograms](https://plot.ly/python/2D-Histogram/) (also check out their close relatives: [2D density plots](https://plot.ly/python/2d-density-plots/) and the more general form: [heatmaps](https://plot.ly/python/heatmaps/).
# 
# While these visualization types explicitly include binning, any type of visualization used with aggregated data can be looked at in the same way. For example, lets say we wanted to look at building construction over time. This would be best viewed as a line graph, but we can still think of our results as being binned by year:

# In[24]:


trace = go.Scatter(
    # I'm choosing BBL here because I know it's a unique key.
    x = ny.groupby('yearbuilt').count()['bbl'].index,
    y = ny.groupby('yearbuilt').count()['bbl']
)

layout = go.Layout(
    xaxis = dict(title = 'Year Built'),
    yaxis = dict(title = 'Number of Lots Built')
)

fig = go.Figure(data = [trace], layout = layout)

py.iplot(fig)


# Something looks off... You're going to have to deal with this imperfect data to answer this first question. 
# 
# But first: some notes on pandas. Pandas dataframes are a different beast than R dataframes, here are some tips to help you get up to speed:
# 
# ---
# 
# Hello all, here are some pandas tips to help you guys through this homework:
# 
# [Indexing and Selecting](https://pandas.pydata.org/pandas-docs/stable/indexing.html): .loc and .iloc are the analogs for base R subsetting, or filter() in dplyr
# 
# [Group By](https://pandas.pydata.org/pandas-docs/stable/groupby.html):  This is the pandas analog to group_by() and the appended function the analog to summarize(). Try out a few examples of this, and display the results in Jupyter. Take note of what's happening to the indexes, you'll notice that they'll become hierarchical. I personally find this more of a burden than a help, and this sort of hierarchical indexing leads to a fundamentally different experience compared to R dataframes. Once you perform an aggregation, try running the resulting hierarchical datafrome through a [reset_index()](https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.reset_index.html).
# 
# [Reset_index](https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.reset_index.html): I personally find the hierarchical indexes more of a burden than a help, and this sort of hierarchical indexing leads to a fundamentally different experience compared to R dataframes. reset_index() is a way of restoring a dataframe to a flatter index style. Grouping is where you'll notice it the most, but it's also useful when you filter data, and in a few other split-apply-combine workflows. With pandas indexes are more meaningful, so use this if you start getting unexpected results.
# 
# Indexes are more important in Pandas than in R. If you delve deeper into the using python for data science, you'll begin to see the benefits in many places (despite the personal gripes I highlighted above.) One place these indexes come in handy is with time series data. The pandas docs have a [huge section](http://pandas.pydata.org/pandas-docs/stable/timeseries.html) on datetime indexing. In particular, check out [resample](https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.resample.html), which provides time series specific aggregation.
# 
# [Merging, joining, and concatenation](https://pandas.pydata.org/pandas-docs/stable/merging.html): There's some overlap between these different types of merges, so use this as your guide. Concat is a single function that replaces cbind and rbind in R, and the results are driven by the indexes. Read through these examples to get a feel on how these are performed, but you will have to manage your indexes when you're using these functions. Merges are fairly similar to merges in R, similarly mapping to SQL joins.
# 
# Apply: This is explained in the "group by" section linked above. These are your analogs to the plyr library in R. Take note of the lambda syntax used here, these are anonymous functions in python. Rather than predefining a custom function, you can just define it inline using lambda.
# 
# Browse through the other sections for some other specifics, in particular reshaping and categorical data (pandas' answer to factors.) Pandas can take a while to get used to, but it is a pretty strong framework that makes more advanced functions easier once you get used to it. Rolling functions for example follow logically from the apply workflow (and led to the best google results ever when I first tried to find this out and googled "pandas rolling")
# 
# Google Wes Mckinney's book "Python for Data Analysis," which is a cookbook style intro to pandas. It's an O'Reilly book that should be pretty available out there.
# 
# ---
# 
# ### Question
# 
# After a few building collapses, the City of New York is going to begin investigating older buildings for safety. The city is particularly worried about buildings that were unusually tall when they were built, since best-practices for safety hadn’t yet been determined. Create a graph that shows how many buildings of a certain number of floors were built in each year (note: you may want to use a log scale for the number of buildings). Find a strategy to bin buildings (It should be clear 20-29-story buildings, 30-39-story buildings, and 40-49-story buildings were first built in large numbers, but does it make sense to continue in this way as you get taller?)

# 
# Let's actually just start examining this data more closely by first looking at the number of lots built per year again. From the PLUTO info file about the "yearbuilt" column:
# 
# "YEAR BUILT is accurate for the decade, but not necessarily for the specific year. Between 1910 and 1985, the majority of YEAR BUILT values are in years ending in 5 or 0. A large number of structures built between 1800s and early 1900s have a YEAR BUILT between 1899 and 1901."
# 
# So let's make a barplot where we plot the number of lots built per decade (1850s to 2010s) instead of per individual year.

# In[25]:


#From https://www.analyticsvidhya.com/blog/2016/01/12-pandas-techniques-python-data-manipulation/.

def binning(col, cut_points, labels=None):
    #Define min and max values:
    minval = col.min()
    maxval = col.max()
    
    #create list by adding min and max to cut_points
    break_points = [minval] + cut_points + [maxval]
    
    #if no labels provided, use default labels 0 ... (n-1)
    if not labels:
        labels = range(len(cut_points)+1)
        
    #Binning using cut function of pandas
    colBin = pd.cut(col,bins=break_points,labels=labels,include_lowest=True)
    return colBin

cut_points = np.ndarray.tolist(np.arange(1859,2019,10))
labels = ['1850s'] + [str(i) + 's' for i in np.ndarray.tolist(np.arange(1860,2020,10))]

ny['decadebuilt'] = binning(ny["yearbuilt"],cut_points,labels)

trace = go.Bar(
    # I'm choosing BBL here because I know it's a unique key.
    x = ny.groupby('decadebuilt').count()['bbl'].index,
    y = ny.groupby('decadebuilt').count()['bbl']
)

layout = go.Layout(
    xaxis = dict(title = 'Year Built'),
    yaxis = dict(title = 'Number of Lots Built')
)

fig = go.Figure(data = [trace], layout = layout)

py.iplot(fig)


# Now that we have the years binned in a sensible manner (into decades), let's move on to also binning by number of stories.

# Start by making a simple histogram of the "numfloors" column. Round up the number of floors for any numbers greater than the whole number (e.g. count partial floors as full floors).

# In[6]:


ny['numfloors'] = np.ceil(ny['numfloors'])

trace = go.Histogram(x=ny["numfloors"],
    nbinsx = 21)

layout = go.Layout(
    xaxis = dict(title = 'Number of floors'),
    yaxis = dict(title = 'Number of buildings')
)

fig = go.Figure(data = [trace], layout = layout)

py.iplot(fig)


# Based on this, it seems reasonable to bin all buildings with 50+ floors together.
# 
# Let's make another histogram just showing only buildings with 9 or fewer floors.

# In[7]:


ny_lowbuildings = ny[(ny['numfloors'] < 10)]

trace = go.Histogram(x=ny_lowbuildings["numfloors"],
    nbinsx=9)

fig = go.Figure(data = [trace], layout = layout)

py.iplot(fig)


# Based on this, plus the fact that buildings higher than 6 stories have unique challenges with getting running water above them in NYC, I propose we look at how many buildings had been built through the end of each decade with 7+ stories, 10+ stories, 20+ stories, 30+ stories, 40+ stories, and 50+ stories.

# In[8]:


heights = [7,10,20,30,40,50]

fig = tools.make_subplots(rows=3,cols=2,
    subplot_titles=[i + ' floors' for i in ['7+','10+','20+','30+','40+','50+']],
    shared_xaxes=True)

i = 0
j = 1                          
                        
for height in heights:
    i = i + 1
    this_or_higher = ny[(ny['numfloors'] >= height)]
    trace = go.Bar(
        x = this_or_higher.groupby('decadebuilt').count()['bbl'].index,
        y = this_or_higher.groupby('decadebuilt').count()['bbl'],
        name = '')
    if i == 1:
        fig.append_trace(trace, 1, 1)
    if i == 2:
        fig.append_trace(trace, 1, 2)
    if i == 3:
        fig.append_trace(trace, 2, 1)
    if i == 4:
        fig.append_trace(trace, 2, 2)
    if i == 5:
        fig.append_trace(trace, 3, 1)
    if i == 6:
        fig.append_trace(trace, 3, 2)
    
fig['layout'].update(height=600, width=800,showlegend=False,
    title='Number of buildings built per decade')
fig['layout']['xaxis1'].update(title='')
fig['layout']['xaxis2'].update(title='')
py.iplot(fig)


# The biggest jump we see is in buildings with 7+ stories, which were built very rarely before 1900.
# 
# We also see that buildings with 20+ or 30+ stories became much more common around the 1920s.
# 
# For buildings with 40+ or 50+ stories, it's a bit harder to tell because these buildings are generally pretty rare. But it seems like they became more common in the 1930s.
# 
# In summary, we should probably pay close attention in our inspections to buildings with 7+ stories built before 1900, buildings with 20+ stories built before 1920, and buildings with 40+ stories built before 1930.

# ## Part 2: Datashader
# 
# Datashader is a library from Anaconda that does away with the need for binning data. It takes in all of your datapoints, and based on the canvas and range returns a pixel-by-pixel calculations to come up with the best representation of the data. In short, this completely eliminates the need for binning your data.
# 
# As an example, lets continue with our question above and look at a 2D histogram of YearBuilt vs NumFloors:

# In[9]:


yearbins = 200
floorbins = 200

yearBuiltCut = pd.cut(ny['yearbuilt'], np.linspace(ny['yearbuilt'].min(), ny['yearbuilt'].max(), yearbins))
numFloorsCut = pd.cut(ny['numfloors'], np.logspace(1, np.log(ny['numfloors'].max()), floorbins))

xlabels = np.floor(np.linspace(ny['yearbuilt'].min(), ny['yearbuilt'].max(), yearbins))
ylabels = np.floor(np.logspace(1, np.log(ny['numfloors'].max()), floorbins))

data = [
    go.Heatmap(z = ny.groupby([numFloorsCut, yearBuiltCut])['bbl'].count().unstack().fillna(0).values,
              colorscale = 'Greens', x = xlabels, y = ylabels)
]

py.iplot(data)


# This shows us the distribution, but it's subject to some biases discussed in the Anaconda notebook [Plotting Perils](https://anaconda.org/jbednar/plotting_pitfalls/notebook). 
# 
# Here is what the same plot would look like in datashader:
# 
# 

# In[10]:


cvs = ds.Canvas(800, 500, x_range = (ny['yearbuilt'].min(), ny['yearbuilt'].max()), 
                                y_range = (ny['numfloors'].min(), ny['numfloors'].max()))
agg = cvs.points(ny, 'yearbuilt', 'numfloors')
view = tf.shade(agg, cmap = cm(Greys9), how='log')
export(tf.spread(view, px=2), 'yearvsnumfloors')


# That's technically just a scatterplot, but the points are smartly placed and colored to mimic what one gets in a heatmap. Based on the pixel size, it will either display individual points, or will color the points of denser regions.
# 
# Datashader really shines when looking at geographic information. Here are the latitudes and longitudes of our dataset plotted out, giving us a map of the city colored by density of structures:

# In[11]:


NewYorkCity   = (( -74.29,  -73.69), (40.49, 40.92))
cvs = ds.Canvas(700, 700, *NewYorkCity)
agg = cvs.points(ny, 'lon', 'lat')
view = tf.shade(agg, cmap = cm(inferno), how='log')
export(tf.spread(view, px=2), 'firery')


# Interestingly, since we're looking at structures, the large buildings of Manhattan show up as less dense on the map. The densest areas measured by number of lots would be single or multi family townhomes.
# 
# Unfortunately, Datashader doesn't have the best documentation. Browse through the examples from their [github repo](https://github.com/bokeh/datashader/tree/master/examples). I would focus on the [visualization pipeline](https://anaconda.org/jbednar/pipeline/notebook) and the [US Census](https://anaconda.org/jbednar/census/notebook) Example for the question below. Feel free to use my samples as templates as well when you work on this problem.
# 
# ### Question
# 
# You work for a real estate developer and are researching underbuilt areas of the city. After looking in the [Pluto data dictionary](https://www1.nyc.gov/assets/planning/download/pdf/data-maps/open-data/pluto_datadictionary.pdf?v=17v1_1), you've discovered that all tax assessments consist of two parts: The assessment of the land and assessment of the structure. You reason that there should be a correlation between these two values: more valuable land will have more valuable structures on them (more valuable in this case refers not just to a mansion vs a bungalow, but an apartment tower vs a single family home). Deviations from the norm could represent underbuilt or overbuilt areas of the city. You also recently read a really cool blog post about [bivariate choropleth maps](http://www.joshuastevens.net/cartography/make-a-bivariate-choropleth-map/), and think the technique could be used for this problem.
# 
# Datashader is really cool, but it's not that great at labeling your visualization. Don't worry about providing a legend, but provide a quick explanation as to which areas of the city are overbuilt, which areas are underbuilt, and which areas are built in a way that's properly correlated with their land value.

# Our two variables of interest here are assessland (land value) and assesstot (total value).
# 
# First, let's make histograms of these so we can decide how to divide into low/medium/high values.

# In[12]:


trace = go.Histogram(x=np.log10(ny["assessland"] + 1),
    xbins=dict(start = 0,end = 10,size=1))

layout = go.Layout(
    xaxis = dict(title = 'log10(land assessment value + 1)'),
    yaxis = dict(title = 'Number of lots')
)

fig = go.Figure(data = [trace], layout = layout)

py.iplot(fig)


# It seems like <10,000, 10,000-99,999, and 100,000+ might be reasonable cutoffs here.
# 
# Run binning, then check counts per bin.

# In[13]:


cut_points = [9999,99999]
labels = ['Low-value land','Mid-value land','High-value land']

ny['landvalue_level'] = binning(ny["assessland"],cut_points,labels)

ny.groupby('landvalue_level').count()['bbl']


# Do similar for total value.

# In[14]:


trace = go.Histogram(x=np.log10(ny["assesstot"] + 1),
    xbins=dict(start = 0,end = 10,size=0.5))

layout = go.Layout(
    xaxis = dict(title = 'log10(total assessment value + 1)'),
    yaxis = dict(title = 'Number of lots')
)

fig = go.Figure(data = [trace], layout = layout)

py.iplot(fig)


# 10^4.5 is around 30,000. So let's set low as <30,000, medium as 30,000-99,999, and high as 100,000+.

# In[15]:


cut_points = [29999,99999]
labels = ['Low-value overall','Mid-value overall','High-value overall']

ny['totalvalue_level'] = binning(ny["assesstot"],cut_points,labels)

ny.groupby('totalvalue_level').count()['bbl']


# Now, let's move on to making the bivariate chloropleth map.

# First, create a combined variable.

# In[16]:


ny['land_and_total_value_level'] = ny['landvalue_level'].astype(str) + '/' + ny['totalvalue_level'].astype(str)

ny['land_and_total_value_level'] = pd.Categorical(ny['land_and_total_value_level'],
                                                  ['Low-value land/Low-value overall',
                                                  'Low-value land/Mid-value overall',
                                                  'Low-value land/High-value overall',
                                                  'Mid-value land/Low-value overall',
                                                  'Mid-value land/Mid-value overall',
                                                  'Mid-value land/High-value overall',
                                                  'High-value land/Low-value overall',
                                                  'High-value land/Mid-value overall',
                                                  'High-value land/High-value overall'])

ny.groupby('land_and_total_value_level').count()['bbl']


# Looks like we might actually want to try decreasing what is considered high-value land? Let's use boundaries of 8,000 and 19,999.

# In[17]:


cut_points = [7999,19999]
labels = ['Low-value land','Mid-value land','High-value land']

ny['landvalue_level'] = binning(ny["assessland"],cut_points,labels)

ny.groupby('landvalue_level').count()['bbl']


# In[18]:


ny['land_and_total_value_level'] = ny['landvalue_level'].astype(str) + '/' + ny['totalvalue_level'].astype(str)

ny['land_and_total_value_level'] = pd.Categorical(ny['land_and_total_value_level'],
                                                  ['Low-value land/Low-value overall',
                                                  'Low-value land/Mid-value overall',
                                                  'Low-value land/High-value overall',
                                                  'Mid-value land/Low-value overall',
                                                  'Mid-value land/Mid-value overall',
                                                  'Mid-value land/High-value overall',
                                                  'High-value land/Low-value overall',
                                                  'High-value land/Mid-value overall',
                                                  'High-value land/High-value overall'])

ny.groupby('land_and_total_value_level').count()['bbl']


# Create color vector and map.

# In[19]:


#From http://www.joshuastevens.net/cartography/make-a-bivariate-choropleth-map/.
#And https://rstudio-pubs-static.s3.amazonaws.com/359867_2aefda9cfaa247938dc9b2be7cc23e55.html#part-2-datashade.

mycol = ['#e8e8e8','#dfb0d6','#be64ac','#ace4e4','#a5add3','#8c62aa','#5ac8c8','#5698b9','#3b4994'] 

colors = {'Low-value land/Low-value overall': mycol[0], 
          'Low-value land/Mid-value overall': mycol[1],
          'Low-value land/High-value overall': mycol[2],
          'Mid-value land/Low-value overall': mycol[3],
          'Mid-value land/Mid-value overall': mycol[4],
          'Mid-value land/High-value overall': mycol[5],
          'High-value land/Low-value overall': mycol[6],
          'High-value land/Mid-value overall': mycol[7],
          'High-value land/High-value overall': mycol[8]}

background = "lightgrey"
export = partial(export_image, background = background, export_path="export")
cm = partial(colormap_select, reverse=(background!="lightgrey"))

NewYorkCity   = (( -74.29,  -73.69), (40.49, 40.92))

cvs = ds.Canvas(700, 700, *NewYorkCity)
agg = cvs.points(ny, 'lon', 'lat', ds.count_cat('land_and_total_value_level'))
view = tf.shade(agg, color_key = colors)
export(tf.spread(view, px=1), 'cloropleth')


# In[20]:


show(create_categorical_legend(colors))


# The areas that have land vs. building prices as expected will be white (both low), light blue, non-teal (both medium), or dark blue (both high).
# 
# Meanwhile areas where land is more relatively valuable than the structures are other shades of blue that lean more teal, while areas where land is less relatively valuable than structures will be in shades of pink or purple.
# 
# Northern Staten Island and southeastern Queens are mid-value land, low-value structures. While a bit further south in Staten Island and a bit further north in Queens from these areas we can find pockets with high-value land, mid-value structures.
# 
# Northern Brooklyn seems to have a high concentration of lots where the land is inexpensive, but the structures on them are high-value.
# 
