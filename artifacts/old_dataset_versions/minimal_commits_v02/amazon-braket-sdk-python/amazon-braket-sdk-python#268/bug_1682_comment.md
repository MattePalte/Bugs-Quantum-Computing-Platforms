A default parameter is a dictionary, and by default they want it to be empty but initializing it in the method signature is wrong, because multiple method calls share the same representation.