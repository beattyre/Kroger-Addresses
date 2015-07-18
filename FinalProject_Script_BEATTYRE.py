# FinalProject_Script_BEATTYRE.py
# Robert Beatty
# GEO 443
# May 9, 2015
# Program that moves shapefiles of LBRS data for five counties into a file geodatabase.
# A new field is added to the attribute tables that includes the mailing address for each point
# Locates the Kroger stores within the county and creates a 1 mile buffer around them
# And finally clips the LBRS shapefiles to only include the addresses within the 1 mile buffer


## TOOLS
# Delete Existing Folder/File: arcpy.Delete_management(in_data, {data_type})
# Create New File Geodatabase: arcpy.CreateFileGDB_management (out_folder_path, out_name, {out_version})
# Create New Feature Dataset: arcpy.CreateFeatureDataset_management (out_dataset_path, out_name, {spatial_reference})
# Move Feature Class/Shapefile to Geodatabase: arcpy.FeatureClassToGeodatabase_conversion(Input_Features, Output_Geodatabase)
# Add Field to Attribute Table: arcpy.AddField_management (in_table, field_name, field_type, {field_precision}, {field_scale}, {field_length}, {field_alias}, {field_is_nullable}, {field_is_required}, {field_domain})
# Create UpdateCursor object: arcpy.da.UpdateCursor (in_table, field_names, {where_clause}, {spatial_reference}, {explode_to_points}, {sql_clause})
# Create New Feature Layer: arcpy.MakeFeatureLayer_management (in_features, out_layer, {where_clause}, {workspace}, {field_info})
# Select Feature Layer by Attribute: arcpy.SelectLayerByAttribute_management (in_layer_or_view, {selection_type}, {where_clause})
# Copy Feature to Feature Class: arcpy.CopyFeatures_management (in_features, out_feature_class, {config_keyword}, {spatial_grid_1}, {spatial_grid_2}, {spatial_grid_3})
# Perform Buffer Analysis: arcpy.Buffer_analysis (in_features, out_feature_class, buffer_distance_or_field, {line_side}, {line_end_type}, {dissolve_option}, {dissolve_field})
# Perform Clip Analysis: arcpy.Clip_analysis (in_features, clip_features, out_feature_class, {cluster_tolerance})

print "Importing modules"
import arcpy
from arcpy import env
from arcpy import da
import os
print "arcpy, arcpy.env, arcpy.da, and os modules have been imported."

# Set environment settings
arcpy.env.workspace = r"E:\School\GEO443\Final_Project\Data\LBRS_files"
outWS = "E:\School\GEO443\Final_Project\Output"
arcpy.env.overwriteOutput = True
print "The workspace is set to: " + arcpy.env.workspace
print "The output workspace is set to: " + outWS
if arcpy.env.overwriteOutput == True:
    print "Program will overwrite any pre-existing files that share a name with an output" 
else: 
    print "Program will not overwrite any pre-existing files that share a name with an output." 
print " "
print " "

try:
    print "BEGINNING OF DATA CONFIGURATION"
    print "-------------------------------"

    # Create file GDB and set it as output workspace
    if arcpy.Exists("E:\School\GEO443\Final_Project\Output\OH_Kroger.gdb") == True:
        arcpy.Delete_management("E:\School\GEO443\Final_Project\Output\OH_Kroger.gdb")
        print "Creating 'OH_Kroger.gdb'." 
        arcpy.CreateFileGDB_management(outWS, "OH_Kroger.gdb", "CURRENT")
        outWS = outWS + '\\' + "OH_Kroger.gdb"
        print "OH_Kroger.gdb has been created."
        print "OH_Kroger.gdb is now the output workspace"
    else:
        arcpy.CreateFileGDB_management(outWS, "OH_Kroger.gdb", "CURRENT")
        print "OH_Kroger.gdb has been created."
        outWS = outWS + "OH_Kroger.gdb"
        print "The output workspace is now set to " + outWS

    # Create spatial reference object and feature datasets for the outputs
    print "Creating feature datasets"
    arcpy.CreateFeatureDataset_management(outWS, "Kroger", "BUT_ADDS.shp")
    arcpy.CreateFeatureDataset_management(outWS, "Buffer", "BUT_ADDS.shp")
    arcpy.CreateFeatureDataset_management(outWS, "Clipped_LBRS", "BUT_ADDS.shp")
    print "Output feature datasets for Kroger, Buffer, and Clipped_LBRS outputs have been created."
    print " "

    fcList = arcpy.ListFeatureClasses()
    for fc in fcList:
        print fc
        # Update Butler County shapefile to include 'STATE' field
        if fc == "BUT_ADDS.shp":
            print "Updating Butler County shapefile to include 'STATE' field."
            arcpy.AddField_management(fc, "STATE", "TEXT", "10")
            with arcpy.da.UpdateCursor(fc, "STATE") as cursor:
                for row in cursor:
                    row[0] == "OH"
                    cursor.updateRow(row)
            print "Butler County shapefile has been updated."
                
        # Migrate shapefiles to file gdb
        arcpy.FeatureClassToGeodatabase_conversion(fc, outWS)
        print fc + ' has been moved to ' + outWS


        lstFields = arcpy.ListFields(fc)     
        ## Add Mailing address field
        print "Update attribute tables with full address field"
        if "FullADD" in lstFields:
            print "Full Address field already exists."
        else:
            arcpy.AddField_management(fc, "FullADD", "TEXT", "50")
            print "FullADD field has been added to " + fc
            
        ## Populate Mailing Address Field
        print "Populating full address field."
        fields = ("LSN", "USPS_CITY", "STATE", "ZIPCODE","FullADD")
        with arcpy.da.UpdateCursor(fc, fields) as cursor:
            for row in cursor:
                row[4] = str((row[0] + ',' + row[1] + ',' + row[2] + ',' + row[3]))
                cursor.updateRow(row)
        print "Full address field has been updated with the points' mailing addresses."
        print " "
except Exception as e:
    print e.message
finally:
    print "END OF DATA CONFIGURATION"
    print " "
    print " "
    
try:
    print "BEGINNING SPATIAL ANALYSIS"
    print "--------------------------"
    # For loop to query kroger locations, create a 1 mile buffer, and clip addresses within the buffer for each county
    for fc in fcList:
        print fc
        ## Query out Kroger Stores and create new shapefile
        print "PERFORMING QUERY OF KROGER LOCATIONS FOR " + fc
        kroger_outWS = outWS + '\\' + "Kroger"
        print "Changed output workspace to: " + kroger_outWS
        # Create where_clause to be used as tool parameter
        if fc == "BUT_ADDS.shp":
            qry = '"COMMENT_" = \'KROGER\''
        else:
            qry = '"COMMENT" = \'KROGER\''
        # Execute attribute selection
        flayer = arcpy.MakeFeatureLayer_management(fc, "kroger_lyr")
        arcpy.SelectLayerByAttribute_management(flayer, "NEW_SELECTION", qry)
        print "Kroger store locations for " + fc + " have been collected."
        # Create shapefile of kroger stores
        copy_outFC = kroger_outWS + '\\' + fc.replace("_ADDS.shp", "_Kroger")
        arcpy.CopyFeatures_management(flayer, copy_outFC)
        print "Kroger store locations saved as: " + copy_outFC
        print " "
   
        ## Create 1 mile buffer around Kroger stores
        print "PERFORMING BUFFER ANALYSIS FOR " + fc
        Buffer_outWS = outWS + '\\' + "Buffer"
        print "Changed output workspace to: " + Buffer_outWS
        # Set up buffer variables
        buff_inFC = copy_outFC
        buff_outFC = Buffer_outWS + '\\' + fc.replace("_ADDS.shp", "_Buff")
        buff_dist = "5280 Feet"
        print "The Buffer dataset is: " + buff_inFC + " and the buffer distance is " + buff_dist
        # Execute buffer analysis
        arcpy.Buffer_analysis(buff_inFC, buff_outFC, buff_dist)
        print "1 Mile buffer for Kroger stores for: " + fc + " has been created and has been saved as: " + buff_outFC
        print " "
        
        ## Clip addresses within buffer
        print "PERFORMING CLIP OF ADDRESSES WITHIN BUFFER AREA FOR " + fc
        Clipped_LBRS_outWS = outWS + '\\' + "Clipped_LBRS"
        print "Changed output workspace to: " + Clipped_LBRS_outWS
        # Set up clip variables
        clip_inFC = fc
        clip_feat = buff_outFC
        clip_outFC = Clipped_LBRS_outWS + '\\' + fc.replace("_ADDS.shp", "_Clip")
        print "Clipping " + fc + " to " + buff_outFC
        # Execute clip
        arcpy.Clip_analysis(clip_inFC, clip_feat, clip_outFC)
        print fc + " has been clipped to " + buff_outFC + " and has been saved as " + clip_outFC
        print " "
        print " "

            
        
except Exception as e:
     print e.message
finally:
    print "END OF SPATIAL ANALYSIS"

del flayer
print "SCRIPT HAS COMPLETED. GOOD STUFF." 
